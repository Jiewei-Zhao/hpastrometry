import os
import shutil
import tempfile
import numpy as np
import warnings

from pathlib import Path
from astropy.io import fits

from .wcs.wcs_add import wcs_add
from .wcs.wcs_check import wcs_check
from .wcs.wcs_prior import wcs_prior
from .wcs.wcs_strip import wcs_strip

from .external.caller_anet import run_anet
from .external.caller_sex import run_sextractor
from .external.caller_scamp import run_scamp

with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    from sip_tpv import pv_to_sip

def run_hpastrometry(infile, outfile,
                     outanetrecalib=None, 
                     outsexcat=None, outsexcheck=None, 
                     outsexxml=None, outsexchecktype=None,
                     outscampwcs=None, outscampcheck=None, 
                     outscampxml=None, outscampchecktype=None,
                     enforce_checkprior=True,
                     enforce_anetsex=True,
                     enforce_anetcpulim=600,
                     enforce_anetds=2,
                     enforce_anetrad=3.14,
                     enforce_anetpixscaleunit='arcsecperpix',
                     enforce_anetpixscalelo=0.1,
                     enforce_anetpixscalehi=100,
                     enforce_scamponlinecatalog='GAIA-DR3',
                     enforce_scamponlineserver='china',
                     enforce_scampprojection='TPV',
                     enforce_legancy=False,
                     verbose=True):
    """
    Run the full High-Precision Astrometry pipeline on a single FITS image.

    This pipeline orchestrates a multi-step process to solve and refine the WCS
    (World Coordinate System) of an astronomical image:
    1. Strips existing (potentially bad) WCS headers.
    2. Estimates image center (RA/Dec) from headers (Priors) to speed up solving.
    3. Runs Astrometry.net for a robust, coarse blind/seeded solution.
    4. Runs SExtractor to generate a source catalog from the coarse image.
    5. Runs SCAMP to compute high-precision astrometric distortion corrections
       against a reference catalog (e.g., Gaia).
    6. Merges the refined WCS solution back into the original image data.

    Args:
        infile (str or Path): Path to the input FITS image.
        outfile (str or Path): Path where the final processed FITS image will be saved.

        # --- Intermediate Output Files (Optional) ---
        # If provided, these files are saved to disk. If None, they are treated as 
        # temporary and deleted after execution.
        outanetrecalib (str, optional): Path to save the coarse WCS FITS from Astrometry.net.
        outsexcat (str, optional): Path to save the SExtractor catalog file (.cat).
        outsexcheck (str, optional): Path to save the SExtractor check-image (e.g., apertures .fits).
        outsexxml (str, optional): Path to save the SExtractor XML output.
        outsexchecktype (str, optional): Type of SExtractor check-image (default: 'APERTURES' if filename provided).
        outscampwcs (str, optional): Path to save the SCAMP header file (.head).
        outscampcheck (str, optional): Path to save the SCAMP check-plot (e.g., .png or .pdf).
        outscampxml (str, optional): Path to save the SCAMP XML output.
        outscampchecktype (str, optional): Type of SCAMP check-plot (default: 'AS_PAIR' if filename provided).

        # --- Configuration Enforcements ---
        enforce_checkprior (bool): If True, attempts to read approximate RA/DEC from 
                                   header keys. If found, limits the Astrometry.net search.
        enforce_anetsex (bool): If True, uses SExtractor for source detection within Astrometry.net.
        enforce_anetcpulim (int): CPU time limit in seconds for the Astrometry.net solver.
        enforce_anetds (int): Downsampling factor for Astrometry.net (speeds up solve, reduces precision slightly).
        enforce_anetrad (float): Search radius in degrees around the prior coordinates (if priors are found).
        enforce_anetpixscaleunit (str): Units for pixel scale (e.g., 'arcsecperpix', 'degwidth').
        enforce_anetpixscalelo (float): Lower bound estimate for pixel scale.
        enforce_anetpixscalehi (float): Upper bound estimate for pixel scale.
        enforce_scamponlinecatalog (str): Reference catalog for SCAMP (e.g., 'GAIA-DR3', '2MASS', 'USNO-B1').
        enforce_scamponlineserver (str): Vizier mirror region for SCAMP. 
                                         Options: 'china', 'usa', 'france', 'japan', 'uk', 'canada'.
        enforce_scampprojection (str): Projection method when executing SCAMP
                                       Options: 'TPV', 'TAN'
        enforce_legancy (bool): If true, using the legancy SIP format of WCS
        verbose (bool): If True, prints progress and execution details to stdout.

    Raises:
        FileNotFoundError: If the input file does not exist.
        subprocess.CalledProcessError: If any external tool (sextractor, scamp, solve-field) fails.
    """

    infile_path = Path(infile).resolve()
    outfile_path = Path(outfile).resolve()

    if not infile_path.exists():
        raise FileNotFoundError(f"Input file not found: {infile}")

    # Use a temporary directory for intermediate files to keep workspace clean
    # If the user requested specific intermediate outputs (e.g., outsexcat), 
    # we will use those paths; otherwise, we use temp paths.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        if verbose:
            print(f"[hpastrometry] Processing {infile_path.name}")
            print(f"[hpastrometry] Working directory: {temp_dir}")

        # ---------------------------------------------------------
        # 1. Prepare Image: Strip WCS
        # ---------------------------------------------------------
        # We strip the WCS to ensure a blind/fresh solve and avoid confusion 
        # with potentially incorrect existing headers.
        stripped_img = temp_path / (infile_path.stem + "_stripped.fits")
        
        if verbose:
            print(f"[hpastrometry] Stripping WCS from input image...")
        
        wcs_strip(str(infile_path), str(stripped_img), verbose=verbose)

        if (wcs_check(str(stripped_img))):
            raise RuntimeError(f"[hpastrometry-FATAL] Can't strip the WCS info.")

        # ---------------------------------------------------------
        # 2. Get Priors (Optional but recommended)
        # ---------------------------------------------------------
        ra_prior = None
        dec_prior = None
        w_prior = None
        h_prior = None
        radius_prior = None

        if enforce_checkprior:
            try:
                # Extract priors from the ORIGINAL file (before stripping)
                # wcs_prior checks WCS first, then raw header keys.
                ra_prior, dec_prior, w_prior, h_prior = wcs_prior(str(infile_path))
                
                # If we found coordinates, set a search radius (e.g., 5 degrees)
                radius_prior = enforce_anetrad 
                
                if verbose:
                    print(f"[hpastrometry] Priors found: RA={ra_prior}, Dec={dec_prior}")
            except Exception as e:
                if verbose:
                    print(f"[hpastrometry] Warning: Could not extract priors. Proceeding with blind solve. ({e})")
                # Ensure we pass None to anet to trigger blind solve
                ra_prior, dec_prior, w_prior, h_prior, radius_prior = None, None, None, None, None

        # ---------------------------------------------------------
        # 3. Coarse Solve: Astrometry.net
        # ---------------------------------------------------------
        # Determine output path for this step
        if outanetrecalib:
            anet_outfile = Path(outanetrecalib).resolve()
        else:
            anet_outfile = temp_path / (infile_path.stem + "_anet.fits")

        if verbose:
            print("[hpastrometry] Running Astrometry.net (Coarse Solve)...")

        run_anet(
            infile=str(stripped_img),
            outfile=str(anet_outfile),
            downsample=enforce_anetds,
            scale_units=enforce_anetpixscaleunit,
            scale_low=enforce_anetpixscalelo,
            scale_high=enforce_anetpixscalehi,
            cpulimit=enforce_anetcpulim,
            use_sextractor=enforce_anetsex,
            ra=ra_prior, dec=dec_prior, radius=radius_prior,
            height=h_prior, width=w_prior,
            verbose=verbose
        )

        # ---------------------------------------------------------
        # 4. Source Extraction: SExtractor
        # ---------------------------------------------------------
        # Run SExtractor on the coarse-solved image to get a source catalog
        if outsexcat:
            sex_catfile = Path(outsexcat).resolve()
        else:
            sex_catfile = temp_path / (infile_path.stem + ".cat")
        
        # Handle optional SExtractor check images
        sex_check_flag = False
        sex_check_name = None
        if outsexcheck:
            sex_check_flag = True
            sex_check_name = str(Path(outsexcheck).resolve())
            if not outsexchecktype:
                outsexchecktype = 'APERTURES'

        sex_xml_name = str(Path(outsexxml).resolve()) if outsexxml else None

        if verbose:
            print("[hpastrometry] Running SExtractor...")

        run_sextractor(
            infile=str(anet_outfile),
            outfile=str(sex_catfile),
            check=sex_check_flag,
            checktype=outsexchecktype,
            outcheck=sex_check_name,
            outxml=sex_xml_name,
            verbose=verbose
        )

        # ---------------------------------------------------------
        # 5. Refined Astrometry: SCAMP
        # ---------------------------------------------------------
        # Run SCAMP using the catalog to compute a precise WCS solution
        if outscampwcs:
            scamp_headfile = Path(outscampwcs).resolve()
        else:
            scamp_headfile = temp_path / (infile_path.stem + ".head")

        # Handle optional SCAMP check plots
        scamp_check_flag = False
        scamp_check_name = None
        if outscampcheck:
            scamp_check_flag = True
            scamp_check_name = str(Path(outscampcheck).resolve())
            if not outscampchecktype:
                outscampchecktype = 'AS_PAIR'

        scamp_xml_name = str(Path(outscampxml).resolve()) if outscampxml else None

        if verbose:
            print("[hpastrometry] Running SCAMP...")

        run_scamp(
            infile=str(sex_catfile),
            outfile=str(scamp_headfile),
            catalog=enforce_scamponlinecatalog,
            region=enforce_scamponlineserver,
            check=scamp_check_flag,
            checktype=outscampchecktype,
            outcheck=scamp_check_name,
            outxml=scamp_xml_name,
            proj=enforce_scampprojection,
            verbose=verbose
        )

        # ---------------------------------------------------------
        # 6. Final Integration: Add WCS
        # ---------------------------------------------------------
        if verbose:
            print(f"[hpastrometry] Applying refined WCS to output: {outfile_path}")
        
        # Apply the SCAMP header to the STRIPPED image to produce the final result
        wcs_add(
            infile=str(stripped_img),
            headfile=str(scamp_headfile),
            outfile=str(outfile_path),
            force=True,
            verbose=verbose
        )

        if (enforce_legancy):
            if verbose:
                print(f"[hpastrometry] Convert to legancy WCS header: {outfile_path}")
            hdul = fits.open(str(outfile_path), mode="update")
            
            # only update the pHDU, which is for image
            for hdu in hdul:
                pv_to_sip(hdu.header)
            
            hdul.close()

        if verbose:
            print("[hpastrometry] Pipeline completed successfully.")