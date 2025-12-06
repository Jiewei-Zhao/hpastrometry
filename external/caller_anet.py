import subprocess
import shutil
import os
import tempfile
from pathlib import Path

def run_anet(infile, outfile, 
             downsample=2, 
             scale_units="arcsecperpix", 
             scale_low=0.1, scale_high=100, 
             cpulimit=600,
             use_sextractor=True,
             ra=None, dec=None, radius=None,
             height=None, width=None,
             verbose=True):
    """
    Run Astrometry.net's solve-field command cleanly (without cluttering workspace).

    Args:
        infile (str or Path): Input FITS image.
        outfile (str or Path): Output FITS image (with WCS added).
        downsample (int): Downsample image for faster solving (default: 2).
        scale_units (str): Units for scale (e.g., 'degwidth', 'arcsecperpix').
        scale_low (float): Lower bound of image scale.
        scale_high (float): Upper bound of image scale.
        cpulimit (int): Time limit in seconds for the solver.
        use_sextractor (bool): If True, use SExtractor to find sources (requires sextractor in path).
        ra, dec (float): Estimated center position (optional, speeds up solve).
        radius (float): Search radius around RA/Dec in degrees.

    Raises:
        subprocess.CalledProcessError: If solve-field fails.
        FileNotFoundError: If the solution file was not generated.
    """
    
    infile_path = Path(infile).resolve()
    outfile_path = Path(outfile).resolve()
    
    # Check if input exists
    if not infile_path.exists():
        raise FileNotFoundError(f"Input file not found: {infile_path}")

    # --- The "Don't Make a Mess" Strategy ---
    # We create a temporary directory. All intermediate files (.axy, .match, etc.)
    # will be generated inside this directory.
    # When the 'with' block exits, the directory and its contents are deleted.
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # 1. Construct the Command
        # We tell solve-field to output everything into the temp_dir
        cmd = [
            'solve-field',
            str(infile_path),
            '--dir', temp_dir,        # Output directory for all intermediate files
            '--no-plots',             # Do not generate PNG plots (saves time and disk)
            '--overwrite',            # Overwrite files in temp dir if needed
            '--downsample', str(downsample), # Speed up by downsampling
            '--cpulimit', str(cpulimit)      # Prevent getting stuck forever
        ]

        # 2. Add Optional Performance  > Parameters
        if ((scale_units != None) and (scale_low != None) and (scale_high != None)):
            cmd.extend(['--scale-units', str(scale_units)])
            cmd.extend(['--scale-low', str(scale_low)])
            cmd.extend(['--scale-high', str(scale_high)])
        else:
            cmd.extend(["--guess-scale"])

        if ((height != None) and (width != None)):
            cmd.extend(['--height', str(height)])
            cmd.extend(['--width', str(width)])
        
        # Use existing SExtractor executable if requested (often better source extraction)
        if (use_sextractor):
            cmd.append('--use-source-extractor')

        # Add Hint for RA/Dec (Drastically speeds up solving if known)
        if ((ra is not None) and (dec is not None) and (radius is not None)):
            symdec = str(dec)
            if (float(dec) > 0):
                symdec = "+" + symdec
            cmd.extend(['--ra', str(ra), '--dec', symdec, '--radius', str(radius)])

        # 3. Handle Output Filename
        # Usually solve-field creates <infile>.new. We want to control the output name.
        # We define a temporary output name inside the temp dir.
        temp_new_fits = Path(temp_dir) / infile_path.with_suffix('.new').name

        # Note: We do NOT use '--new-fits' flag pointing to the final destination 
        # because solve-field behavior with --dir and absolute paths can be tricky.
        # It's safer to let it write to temp, and we move it later.
        
        # 4. Execute
        # print(f"Executing: {' '.join(cmd)}") # Debugging
        try:
            # capture_output=True suppresses the massive stdout spam from astrometry.net
            subprocess.run(cmd, check=True, cwd=temp_dir, capture_output=True, text=True) 
        except subprocess.CalledProcessError as e:
            print(f"[hpastrometry-FATAL] Astrometry.net failed to solve {infile_path.name}")
            # Optional: print(e.stdout) if you need to debug why it failed
            print("[hpastrometry-FATAL] Last standard output: ")
            print(e.stdout)
            print("[hpastrometry-FATAL] Last standard errors: ")
            print(e.stderr)
            raise

        # 5. Retrieve the Result
        # Check if the "solved" marker file exists
        # solve-field creates a file named <base>.solved if successful
        # But checking for the .new file is more practical for our goal
        
        if temp_new_fits.exists():
            # Move the result from temp dir to the user's desired location
            shutil.move(str(temp_new_fits), str(outfile_path))
            if (verbose):
                print(f"[hpastrometry-anet] Solved successfully. WCS file saved to: {outfile_path}")
        else:
            # If the .new file wasn't created, the solve likely failed (not enough stars, etc.)
            print(f"[hpastrometry-FATAL] Could not solve field for: {infile_path}")
            # You might want to raise an error here or just return False
            raise FileNotFoundError("[hpastrometry-FATAL] Astrometry.net finished but did not produce a solution file.")