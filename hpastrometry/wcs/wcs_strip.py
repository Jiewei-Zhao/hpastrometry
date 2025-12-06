import os
from astropy.io import fits

def wcs_strip(infile, outfile=None, verbose=True):
    """
    Completely remove all WCS information from a FITS header, including 
    standard WCS, SIP (Astrometry.net), and PV (SCAMP) distortion keys.
    
    Args:
        infile (str): Path to the input FITS file.
        outfile (str, optional): Path to save the result. 
                                 If None, the input file is overwritten.
    """
    if outfile is None:
        outfile = infile

    input_abs = os.path.abspath(infile)
    output_abs = os.path.abspath(outfile)
    
    open_mode = 'update' if input_abs == output_abs else 'readonly'
        
    # List of WCS keyword prefixes or exact keys to remove.
    # 1. Standard WCS: CTYPE, CRVAL, CRPIX, CD matrix, PC matrix, etc.
    # 2. SIP Distortion (Astrometry.net): A_*, B_*, AP_*, BP_*
    # 3. SCAMP/PV Distortion: PV*
    # 4. Systems: RADESYS, EQUINOX, POLE
    wcs_prefixes = [
        'CTYPE', 'CRVAL', 'CRPIX', 'CD1_', 'CD2_', 'CDELT', 'CUNIT', 'CROTA',
        'PC1_', 'PC2_', 'RADESYS', 'EQUINOX', 'LONPOLE', 'LATPOLE', 'RADECSYS', 'RADESYSa',
        'PV1_', 'PV2_',          # SCAMP/PV distortion keys
        'A_', 'B_', 'AP_', 'BP_' # SIP distortion keys
    ]
    
    # Specific keys that might not match simple prefixes
    wcs_exact_keys = ['CV1_1', 'CV1_2', 'CV2_1', 'CV2_2', 'SIPCODE']

    with fits.open(infile, mode=open_mode) as hdul:
        header = hdul[0].header
        
        # Collect keys to remove (avoid modifying dictionary while iterating)
        keys_to_remove = []
        
        for key in header.keys():
            # Check against prefixes
            for prefix in wcs_prefixes:
                if key.startswith(prefix):
                    keys_to_remove.append(key)
                    break
            
            # Check against exact matches
            if key in wcs_exact_keys:
                keys_to_remove.append(key)

        # Execute removal
        if keys_to_remove:
            for key in keys_to_remove:
                try:
                    del header[key]
                except KeyError:
                    pass
            if (verbose):
                print(f"[hpastrometry-WCS] Removed {len(keys_to_remove)} WCS keywords from {infile}.")
        else:
            if (verbose):
                print(f"[hpastrometry-WCS] No WCS keywords found in {infile}.")
        
        # Save changes
        if outfile == infile:
            hdul.flush()  # Update in-place
        else:
            hdul.writeto(outfile, overwrite=True)