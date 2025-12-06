import subprocess
from pathlib import Path

def run_sextractor(infile, outfile, 
                   check=False, checktype='APERTURES', outcheck=None, 
                   outxml=None, verbose=True):
    """
    Run SExtractor on a FITS image.

    Args:
        infile (str or Path): Path to the input FITS image.
        outfile (str or Path): Path to the output catalog file.
        check (bool): Whether to generate a check-image (e.g., aperture map, segmentation map).
        checktype (str): Type of the check-image (e.g., 'APERTURES', 'SEGMENTATION', 'BACKGROUND').
        outcheck (str or Path): Path to the output check-image file (required if check is True).
        outxml (str or Path): Path to the output XML VOTable (optional).

    Raises:
        FileNotFoundError: If the configuration file is missing.
        ValueError: If arguments for check-image are invalid.
        subprocess.CalledProcessError: If SExtractor fails during execution.
    """
    
    # 1. Resolve Paths
    # Locate the current script file
    current_file = Path(__file__).resolve()
    
    # Navigate up to the package root directory (hpastrometry)
    package_root = current_file.parent.parent
    
    # Define the configuration directory
    config_dir = package_root / 'config'
    
    # Define absolute paths for all SExtractor configuration files
    sex_cfg     = config_dir / 'sex.cfg'
    sex_param   = config_dir / 'sex.param'
    sex_filter  = config_dir / 'sexfwhm5p0s99.conv'
    sex_nnw     = config_dir / 'sex.nnw'

    # Ensure the main config file exists
    if not sex_cfg.exists():
        raise FileNotFoundError(f"[hpastrometry-FATAL] SExtractor config file not found: {sex_cfg}")

    # 2. Construct the Base Command
    # We use a list for subprocess to handle spaces in paths safely.
    cmd = [
        'sextractor',
        str(infile),
        '-c', str(sex_cfg),
        '-CATALOG_NAME', str(outfile),
        '-PARAMETERS_NAME', str(sex_param),
        '-FILTER_NAME', str(sex_filter),
        '-STARNNW_NAME', str(sex_nnw)
    ]
    
    # 3. Handle Check Image (Optional)
    if check:
        # Validate the check image type
        valid_checktypes = [
            "BACKGROUND", "BACKGROUND_RMS", "MINIBACKGROUND",
            "MINIBACK_RMS", "-BACKGROUND", "FILTERED",
            "OBJECTS", "-OBJECTS", "SEGMENTATION", "APERTURES"
        ]
        
        if checktype not in valid_checktypes:
            raise ValueError(f"[hpastrometry-FATAL] Check file type not supported: {checktype}.")
        
        # Ensure output filename is provided
        if outcheck is None:
            raise ValueError("[hpastrometry-FATAL] Output file missing. Please specify an 'outcheck' file path.")
        
        # FIX: Split the flag and the value into separate list elements
        cmd.extend(['-CHECKIMAGE_TYPE', str(checktype)])
        cmd.extend(['-CHECKIMAGE_NAME', str(outcheck)])

    # 4. Handle XML Output (Optional)
    if outxml is not None:
        # FIX: Split flags and values here as well
        cmd.extend(['-WRITE_XML', 'Y'])
        cmd.extend(['-XML_NAME', str(outxml)])

    # 5. Execute Command
    try:
        # Optional: Print command for debugging
        # print(f"Executing: {' '.join(cmd)}")
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        if (verbose):
            print(f"[hpastrometry-sex] SExtractor finished successfully. Output: {outfile}")
        
    except subprocess.CalledProcessError as e:
        print(f"[hpastrometry-FATAL] Error running SExtractor. Return code: {e.returncode}")
        print(f"[hpastrometry-FATAL] Last standard output: ")
        print(e.stdout)
        print(f"[hpastrometry-FATAL] Last standard errors: ")
        print(e.stderr)
        raise