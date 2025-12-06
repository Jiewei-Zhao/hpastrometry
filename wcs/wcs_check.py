from astropy.io import fits
from astropy.wcs import WCS
import warnings

def wcs_check(infile):

    """
    Check if a FITS file contains valid celestial WCS information.
    
    Args:
        infile (str): Path to the FITS file.
        
    Returns:
        bool: True if valid celestial WCS exists, False otherwise.
    """
    
    try:
        # Open the file in readonly mode to read the header
        with fits.open(infile, mode='readonly') as hdul:
            header = hdul[0].header
            
            # Parse the WCS from the header.
            # fix=False prevents astropy from guessing missing keywords, 
            # providing a stricter check.
            w = WCS(header, fix=False)
            
            if w.is_celestial:
                return True
            else:
                return False
            
    except Exception as e:

        return False