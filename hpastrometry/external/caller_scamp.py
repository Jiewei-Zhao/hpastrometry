import subprocess
from pathlib import Path

def run_scamp(infile, outfile, catalog='GAIA-DR3', region='china', proj='TAN',
              check=False, checktype='AS_PAIR', outcheck=None, outxml=None,
              verbose=True):
    """
    Run SCAMP to compute astrometric and photometric solutions.

    Args:
        infile (str or Path): Input SExtractor catalog file (e.g., .cat or .fits).
        outfile (str or Path): Output header file path (e.g., .head).
        catalog (str): Name of the reference catalog (e.g., 'GAIA-DR3', '2MASS').
        region (str): Region code for the Vizier mirror server (default: 'china').
                      Options: 'china', 'usa', 'france', 'japan', 'uk', 'canada', 'india', 'southafrica'.
        proj (str): Projection method when executing SCAMP
                    Options: 'TPV', 'TAN'
        check (bool): Whether to generate check-plots.
        checktype (str): Type of the check-plot (e.g., 'AS_PAIR', 'AS_REFPAIR', 'AS_XCORR').
        outcheck (str or Path): Filename for the output check-plot (e.g., 'scamp_check.png').
        outxml (str or Path): Path to the output XML VOTable (optional).

    Raises:
        FileNotFoundError: If the configuration file is missing.
        ValueError: If arguments (region, catalog, checktype) are invalid.
        subprocess.CalledProcessError: If SCAMP fails during execution.
    """

    # 1. Define Valid Constants 
    
    # Map friendly country names to actual Vizier server URLs
    MIRRORS = {
        'china':       'vizier.china-vo.org',
        'usa':         'vizier.cfa.harvard.edu',
        'france':      'vizier.unistra.fr',
        'japan':       'vizier.nao.ac.jp',
        'uk':          'vizier.ast.cam.ac.uk',
        'canada':      'vizier.hia.nrc.ca',
        'india':       'vizier.iucaa.in',
        'southafrica': 'viziersaao.chpc.ac.za'
    }

    VALID_CATALOGS = {
        'USNO-A2', 'USNO-B1', 'GSC-2.3', 'TYCHO-2', 'UCAC-4', 'URAT-1', 
        'NOMAD-1', 'PPMX', 'CMC-15', '2MASS', 'DENIS-3', 'SDSS-R9', 
        'SDSS-R12', 'IGSL', 'GAIA-DR1', 'GAIA-DR2', 'GAIA-EDR3', 
        'GAIA-DR3', 'PANSTARRS-1', 'ALLWISE', 'UNWISE'
    }

    VALID_CHECKTYPES = {'AS_PAIR', 'AS_REFPAIR', 'AS_XCORR'}

    # 2. Resolve Paths 
    
    current_file = Path(__file__).resolve()
    package_root = current_file.parent.parent
    config_dir = package_root / 'config'
    
    # Assuming the config file is named 'scamp.cfg' inside the config directory
    scamp_cfg = config_dir / 'scamp.cfg'

    if not scamp_cfg.exists():
        raise FileNotFoundError(f"[hpastrometry-FATAL] SCAMP config file not found: {scamp_cfg}")

    # 3. Validate Arguments 

    # Validate Region/Mirror
    if region.lower() not in MIRRORS:
        raise ValueError(f"[hpastrometry-FATAL] Invalid region: '{region}'. Available: {list(MIRRORS.keys())}")
    server_url = MIRRORS[region.lower()]

    # Validate Catalog
    if catalog not in VALID_CATALOGS:
        # Warning: You might want to allow custom catalogs, if so, remove this check or make it a warning.
        raise ValueError(f"[hpastrometry-FATAL] Invalid reference catalog: '{catalog}'.")
    
    # valid projection
    if proj not in ['TAN', 'TPV']:
        # Warning: You might want to allow custom catalogs, if so, remove this check or make it a warning.
        raise ValueError(f"[hpastrometry-FATAL] Invalid projection method: '{proj}'.")


    # 4. Construct Command 

    cmd = [
        'scamp',
        str(infile),
        '-c', str(scamp_cfg),
        '-HEADER_NAME', str(outfile),
        '-REF_SERVER', str(server_url),
        '-ASTREF_CATALOG', str(catalog),
        '-PROJECTION_TYPE', str(proj),
    ]

    # 5. Handle Check Plots (Optional) 
    
    if check:
        if checktype not in VALID_CHECKTYPES:
            raise ValueError(f"[hpastrometry-FATAL] Check type not supported: {checktype}. Valid: {VALID_CHECKTYPES}")
        
        if outcheck is None:
            raise ValueError(f"[hpastrometry-FATAL] Output filename missing. Please specify 'outcheck' (e.g., 'fwhm.png').")

        # Note: Scamp uses -CHECKPLOT_TYPE and -CHECKPLOT_NAME (different from SExtractor's CHECKIMAGE)
        cmd.extend(['-CHECKIMAGE_TYPE', str(checktype)])
        cmd.extend(['-CHECKIMAGE_NAME', str(outcheck)])

    # 6. Handle XML Output (Optional) 

    if outxml is not None:
        cmd.extend(['-WRITE_XML', 'Y'])
        cmd.extend(['-XML_NAME', str(outxml)])

    # 7. Execute Command

    try:
        # Optional: Print for debugging
        # print(f"Executing: {' '.join(cmd)}")
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        if (verbose):
            print(f"[hpastrometry-scamp] SCAMP finished successfully. Header written to: {outfile}")

    except subprocess.CalledProcessError as e:
        print(f"[hpastrometry-FATAL] Error running SCAMP. Return code: {e.returncode}")
        print(f"[hpastrometry-FATAL] Last standard output: ")
        print(e.stdout)
        print(f"[hpastrometry-FATAL] Last standard errors: ")
        print(e.stderr)
        raise