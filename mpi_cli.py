import argparse
import sys
import os
from pathlib import Path
import math

# Try importing mpi4py
try:
    from mpi4py import MPI
except ImportError:
    print("Error: 'mpi4py' is required for this script.", file=sys.stderr)
    print("Please install it via: pip install mpi4py", file=sys.stderr)
    sys.exit(1)

from .astrometry import run_hpastrometry

def chunk_list(data_list, num_chunks):
    """Splits a list into roughly equal chunks."""
    avg = len(data_list) / float(num_chunks)
    out = []
    last = 0.0
    while last < len(data_list):
        out.append(data_list[int(last):int(last + avg)])
        last += avg
    return out

def main():
    # --- MPI Setup ---
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # --- Argument Parsing ---
    # We define arguments inside main, but typically only Rank 0 needs to process them deeply,
    # though it's safer if all parse them to have the config values available.
    
    parser = argparse.ArgumentParser(
        description="High-Precision Astrometry Pipeline (MPI Version). "
                    "Process a list of files in parallel using mpirun."
    )

    # --- Batch Processing Arguments ---
    parser.add_argument("filelist", help="Path to a text file containing the list of input FITS files (one per line).")
    parser.add_argument("outdir", help="Directory to save output files.")
    parser.add_argument("suffix", help="Suffix for output files (e.g., '_refined'). Extension .fits will be appended automatically.")

    # --- Configuration Enforcements (Same as single version) ---
    conf_group = parser.add_argument_group('Configuration', 'Pipeline tuning parameters.')
    
    conf_group.add_argument("--no-priors", dest="enforce_checkprior", action="store_false", default=True,
                            help="Disable looking for RA/Dec priors in the header.")
    conf_group.add_argument("--no-anet-sex", dest="enforce_anetsex", action="store_false", default=True,
                            help="Do not use SExtractor inside Astrometry.net.")
    conf_group.add_argument("--cpu-limit", dest="enforce_anetcpulim", type=int, default=600,
                            help="CPU time limit for Astrometry.net (seconds).")
    conf_group.add_argument("--downsample", dest="enforce_anetds", type=int, default=2,
                            help="Downsampling factor.")
    conf_group.add_argument("--radius", dest="enforce_anetrad", type=float, default=3.14,
                            help="Search radius in degrees (used if priors are found).")
    conf_group.add_argument("--scale-unit", dest="enforce_anetpixscaleunit", default="arcsecperpix",
                            help="Pixel scale units.")
    conf_group.add_argument("--scale-low", dest="enforce_anetpixscalelo", type=float, default=0.1,
                            help="Lower bound for pixel scale.")
    conf_group.add_argument("--scale-high", dest="enforce_anetpixscalehi", type=float, default=100.0,
                            help="Upper bound for pixel scale.")
    conf_group.add_argument("--catalog", dest="enforce_scamponlinecatalog", default="GAIA-DR3",
                            help="Reference catalog for SCAMP.")
    conf_group.add_argument("--server", dest="enforce_scamponlineserver", default="china",
                            help="Vizier mirror region.")
    conf_group.add_argument("--projection", dest="enforce_scampprojection", default="TAN",
                            help="SCAMP projection method.")
    conf_group.add_argument("--legancy", dest="enforce_legancy", action='store_true', default=False,
                            help="Using the legancy SIP WCS header.")
    
    # Note: We disable intermediate outputs in MPI mode to avoid I/O flooding and clutter
    parser.add_argument("--verbose", action="store_true", default=False, 
                        help="Enable verbose output (Output may be interleaved from different ranks).")

    args = parser.parse_args()

    # --- Work Distribution ---
    local_files = []

    if rank == 0:
        # 1. Prepare Output Directory
        out_path = Path(args.outdir).resolve()
        if not out_path.exists():
            try:
                out_path.mkdir(parents=True, exist_ok=True)
                print(f"[MPI-Master] Created output directory: {out_path}")
            except OSError as e:
                print(f"[MPI-Master] Error creating directory: {e}")
                comm.Abort(1)

        # 2. Read File List
        list_path = Path(args.filelist)
        if not list_path.exists():
            print(f"[MPI-Master] File list not found: {list_path}")
            comm.Abort(1)
            
        all_files = []
        
        try:
            with open(list_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()
                    # Skip empty lines and comments
                    if stripped and not stripped.startswith('#'):
                        all_files.append(stripped)
        except Exception as e:
            print(f"[MPI-Master] Error reading file list: {e}")
            comm.Abort(1)
        
        # Check if we actually found files
        if not all_files:
            print("[MPI-Master] Error: File list is empty or unreadable.")
            comm.Abort(1)

        total_files = len(all_files)
        print(f"[MPI-Master] Found {total_files} files to process on {size} ranks.")

        # 3. Distribute Work
        chunks = chunk_list(all_files, size)
    else:
        chunks = None
        out_path = None

    # Broadcast the output path to all ranks (so they know where to write)
    out_path = comm.bcast(out_path, root=0)
    
    # Scatter the file lists
    local_files = comm.scatter(chunks, root=0)

    # --- Processing Loop ---
    # Synchronize before starting
    comm.Barrier()

    processed_count = 0
    error_count = 0

    if args.verbose:
        print(f"[Slave {rank}] Received {len(local_files)} files.", flush=True)

    for infile_str in local_files:
        infile = Path(infile_str)
        
        # Construct output filename: <original_stem><suffix>.fits
        # Example: image001.fits -> image001_refinedwcs.fits
        outfile_name = f"{infile.stem}{args.suffix}.fits"
        outfile = out_path / outfile_name

        try:
            if args.verbose:
                print(f"[Slave {rank}] Start: {infile.name}", flush=True)

            run_hpastrometry(
                infile=str(infile),
                outfile=str(outfile),
                # Disable intermediate files for MPI runs to save disk I/O
                outanetrecalib=None,
                outsexcat=None, outsexcheck=None, outsexxml=None,
                outscampwcs=None, outscampcheck=None, outscampxml=None,
                # Config
                enforce_checkprior=args.enforce_checkprior,
                enforce_anetsex=args.enforce_anetsex,
                enforce_anetcpulim=args.enforce_anetcpulim,
                enforce_anetds=args.enforce_anetds,
                enforce_anetrad=args.enforce_anetrad,
                enforce_anetpixscaleunit=args.enforce_anetpixscaleunit,
                enforce_anetpixscalelo=args.enforce_anetpixscalelo,
                enforce_anetpixscalehi=args.enforce_anetpixscalehi,
                enforce_scamponlinecatalog=args.enforce_scamponlinecatalog,
                enforce_scamponlineserver=args.enforce_scamponlineserver,
                enforce_scampprojection=args.enforce_scampprojection,
                enforce_legancy=args.enforce_legancy,
                verbose=False # Force internal function quiet, we handle logs here
            )
            processed_count += 1
            if args.verbose:
                print(f"[Slave {rank}] Done: {infile.name}", flush=True)

        except Exception as e:
            error_count += 1
            print(f"[Slave {rank}] FAILED: {infile.name} | Error: {e}", flush=True)

    # --- Summary ---
    comm.Barrier()
    
    # Gather stats
    total_processed = comm.reduce(processed_count, op=MPI.SUM, root=0)
    total_errors = comm.reduce(error_count, op=MPI.SUM, root=0)

    if rank == 0:
        print("-" * 40)
        print("MPI Run Finished")
        print(f"Total Files Processed: {total_processed}")
        print(f"Total Errors:          {total_errors}")
        print("-" * 40)

if __name__ == "__main__":
    main()