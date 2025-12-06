import argparse
import sys
from .astrometry import run_hpastrometry

def main():
    parser = argparse.ArgumentParser(
        description="High-Precision Astrometry Pipeline (hpastrometry). "
                    "Solves WCS using Astrometry.net, extracts sources with SExtractor, "
                    "and refines the solution using SCAMP."
                    "\nAuthor: Jiewei Zhao <meow.jiewei.zhao@gmail.com>\n"
    )

    # --- Positional Arguments ---
    parser.add_argument("infile", help="Path to input FITS image.")
    parser.add_argument("outfile", help="Path to output processed FITS image.")

    # --- Intermediate Output Options ---
    out_group = parser.add_argument_group('Intermediate Outputs', 'Save intermediate files for debugging or inspection.')
    
    out_group.add_argument("--save-anet", dest="outanetrecalib", metavar="FILE",
                           help="Save the coarse WCS FITS from Astrometry.net.")
    
    out_group.add_argument("--save-sex-cat", dest="outsexcat", metavar="FILE",
                           help="Save the SExtractor catalog (.cat).")
    
    out_group.add_argument("--save-sex-check", dest="outsexcheck", metavar="FILE",
                           help="Save the SExtractor check-image.")
    
    out_group.add_argument("--save-sex-xml", dest="outsexxml", metavar="FILE",
                           help="Save the SExtractor XML output.")
    
    out_group.add_argument("--sex-check-type", dest="outsexchecktype", default="APERTURES",
                           help="Type of SExtractor check-image (default: APERTURES).")

    out_group.add_argument("--save-scamp-head", dest="outscampwcs", metavar="FILE",
                           help="Save the SCAMP header file (.head).")
    
    out_group.add_argument("--save-scamp-check", dest="outscampcheck", metavar="FILE",
                           help="Save the SCAMP check-plot (e.g., .png).")
    
    out_group.add_argument("--save-scamp-xml", dest="outscampxml", metavar="FILE",
                           help="Save the SCAMP XML output.")
    
    out_group.add_argument("--scamp-check-type", dest="outscampchecktype", default="AS_PAIR",
                           help="Type of SCAMP check-plot (default: AS_PAIR).")

    # --- Configuration Enforcements ---
    conf_group = parser.add_argument_group('Configuration', 'Pipeline tuning parameters.')

    # Boolean flags: Default is True, so we provide flags to disable them.
    conf_group.add_argument("--no-priors", dest="enforce_checkprior", action="store_false", default=True,
                            help="Disable looking for RA/Dec priors in the header.")
    
    conf_group.add_argument("--no-anet-sex", dest="enforce_anetsex", action="store_false", default=True,
                            help="Do not use SExtractor inside Astrometry.net (use simple built-in).")

    # Numeric/String parameters
    conf_group.add_argument("--cpu-limit", dest="enforce_anetcpulim", type=int, default=600,
                            help="CPU time limit for Astrometry.net (seconds).")
    
    conf_group.add_argument("--downsample", dest="enforce_anetds", type=int, default=2,
                            help="Downsampling factor for Astrometry.net.")
    
    conf_group.add_argument("--radius", dest="enforce_anetrad", type=float, default=3.14,
                            help="Search radius in degrees (used if priors are found).")

    conf_group.add_argument("--scale-unit", dest="enforce_anetpixscaleunit", default="arcsecperpix",
                            help="Pixel scale units (e.g., arcsecperpix, degwidth).")
    
    conf_group.add_argument("--scale-low", dest="enforce_anetpixscalelo", type=float, default=0.1,
                            help="Lower bound for pixel scale.")
    
    conf_group.add_argument("--scale-high", dest="enforce_anetpixscalehi", type=float, default=100.0,
                            help="Upper bound for pixel scale.")

    conf_group.add_argument("--catalog", dest="enforce_scamponlinecatalog", default="GAIA-DR3",
                            help="Reference catalog for SCAMP (default: GAIA-DR3).")
    
    conf_group.add_argument("--server", dest="enforce_scamponlineserver", default="china",
                            help="Vizier mirror region (default: china).")
    
    conf_group.add_argument("--projection", dest="enforce_scampprojection", default="TAN",
                            help="SCAMP projection method.")

    conf_group.add_argument("--legancy", dest="enforce_legancy", action='store_true', default=False,
                            help="Using the legancy SIP WCS header.")

    parser.add_argument("--verbose", dest="verbose", action='store_true', default=False,
                        help="Suppress verbose output.")

    args = parser.parse_args()

    try:
        run_hpastrometry(
            infile=args.infile,
            outfile=args.outfile,
            outanetrecalib=args.outanetrecalib,
            outsexcat=args.outsexcat,
            outsexcheck=args.outsexcheck,
            outsexxml=args.outsexxml,
            outsexchecktype=args.outsexchecktype,
            outscampwcs=args.outscampwcs,
            outscampcheck=args.outscampcheck,
            outscampxml=args.outscampxml,
            outscampchecktype=args.outscampchecktype,
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
            verbose=args.verbose
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()