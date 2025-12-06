from astropy.io import fits
from astropy.wcs import WCS
import warnings

def wcs_prior(infile):
    """
    Extract the approximate RA and DEC of the image center from a FITS file.
    
    It first attempts to calculate the center using the WCS standard. 
    If that fails, it searches for raw header keywords.
    
    Args:
        infile (str): Path to the FITS file.
        
    Returns:
        tuple: (ra, dec, naxis1, naxis2) The Right Ascension and Declination (usually in degrees).
        
    Raises:
        KeyError: If valid WCS or RA/DEC keywords cannot be found.
    """
    
    try:
        # Open the file in readonly mode to read the header.
        # Using 'with' ensures the file is properly closed after reading.
        with fits.open(infile, mode='readonly') as hdul:
            header = hdul[0].header
            
            # --- Method 1: Use Astropy WCS (Preferred) ---
            # This is robust because it handles projection and rotation.
            try:
                # Suppress FITS fixed warnings during WCS parsing
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    w = WCS(header)
                
                # Check if the WCS object contains celestial coordinates
                if w.is_celestial:
                    # Get image dimensions to calculate the center pixel
                    naxis1 = header.get('NAXIS1', 0)
                    naxis2 = header.get('NAXIS2', 0)
                    
                    # Calculate center pixel coordinates (0-indexed)
                    cx = naxis1 / 2.0
                    cy = naxis2 / 2.0
                    
                    # Convert pixel coordinates to world coordinates (RA, Dec)
                    center_coord = w.pixel_to_world(cx, cy)
                    
                    # Return values in degrees
                    return center_coord.ra.deg, center_coord.dec.deg, naxis1, naxis2
            except Exception:
                # If WCS parsing fails, silently continue to Method 2
                pass

            # --- Method 2: Search for Raw Header Keywords (Fallback) ---
            # Different telescopes use different keywords for coordinates.
            ra_keys = ['RA', 'TEL-RA', 'RAD', 'OBJCTRA', 'CRVAL1', 'MN_RA', 'CAT-RA']
            dec_keys = ['DEC', 'TEL-DEC', 'DECD', 'OBJCTDEC', 'CRVAL2', 'MN_DEC', 'CAT-DEC']
            
            found_ra = None
            found_dec = None
            
            # Iterate through possible RA keys
            for key in ra_keys:
                if key in header:
                    found_ra = header[key]
                    break
            
            # Iterate through possible DEC keys
            for key in dec_keys:
                if key in header:
                    found_dec = header[key]
                    break
            
            naxis1 = header.get('NAXIS1', 0)
            naxis2 = header.get('NAXIS2', 0)
                    
            # If both coordinates were found in the header
            if found_ra is not None and found_dec is not None:
                return found_ra, found_dec, naxis1, naxis2

            # --- Failure ---
            # If logic reaches here, no coordinates were found
            raise KeyError("[hpastrometry-FATAL] Missing Coordinate Keys")

    except Exception as e:
        # Raise the custom error message as requested
        raise KeyError(f"[hpastrometry-FATAL] No RA and DEC key found in '{infile}'. "
                       "Try not stripping the old WCS or re-check your telescope. "
                       f"(Original error: {str(e)})")
    