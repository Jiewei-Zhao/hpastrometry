# hpastrometry: High-Precision Astrometry Pipeline

**hpastrometry** is a Python wrapper pipeline that automates the process of generating high-precision World Coordinate System (WCS) solutions for astronomical images. 

It orchestrates a robust workflow by combining three powerful external tools:
1.  **Astrometry.net (`solve-field`)**: For robust blind or seeded coarse WCS solutions.
2.  **SExtractor**: For high-quality source extraction.
3.  **SCAMP**: For computing high-precision astrometric and photometric distortion corrections against reference catalogs (e.g., Gaia-DR3).

Note: It's better to compile SExtractor and SCAMP using Intel toolchain and enable mkl and parallel execution. Also, if you install Astrometry.net from apt/yum/aur, it's necessary to turn on the parallel solver in '/etc/astrometry.cfg'

Note2: This pipeline is optimized with the help of Google Gemini AI and I have checked the code twice. But I can't guarantee there're no bugs in the code. Use with caution and check the output result!

---

## 📋 Prerequisites

Since this package is a wrapper, **you must have the following external software installed and available in your system PATH**:

1.  **Astrometry.net** (`solve-field` command)
2.  **SExtractor** (`sextractor` or `source-extractor` command)
3.  **SCAMP** (`scamp` command)

### Python Dependencies
*   Python >= 3.8
*   `numpy`
*   `astropy`
*   `sip_tpv`
*   `mpi4py` (Optional, for parallel processing)

Note: when install `sip_tpv` through pip, they will throw some errors of `zogy`, but it doesn't matter, just ignore it.

---

## 🛠️ Installation

### 1. Standard Installation
To install the package and the standard CLI tool:

```bash
cd hpastrometry
pip install .
```

### 2. Installation with MPI Support
If you plan to use the parallel processing feature (`hpastrometry-mpi`), you need `mpi4py`.

**For standard Python environments:**
```bash
pip install ".[mpi]"
```

**For Anaconda / Intel Python users (Recommended):**
To avoid library conflicts (the "suspicious MPI environment" warning), install `mpi4py` via Conda instead of pip:
```bash
conda install mpi4py
pip install .
```

---

## 🚀 Usage

### 1. Single Image Mode (`hpastrometry`)

Use this command to process a single FITS image.

**Basic Syntax:**
```bash
hpastrometry <input_image.fits> <output_image.fits>
```

**Advanced Example:**
Solve an image, disable priors, save intermediate check-plots, and use a specific catalog:
```bash
hpastrometry raw_data.fits refined_data.fits \
    --no-priors \
    --save-scamp-check distortion_map.png \
    --catalog GAIA-DR3 \
    --radius 5.0
```

**Options:**
*   `--save-anet`, `--save-sex-cat`, `--save-scamp-head`: Save intermediate files.
*   `--catalog`: Choose reference catalog (default: GAIA-DR3).
*   `--scale-low`, `--scale-high`: Constrain pixel scale to speed up solving.
*   Run `hpastrometry --help` for a full list.

---

### 2. Parallel Batch Mode (`hpastrometry-mpi`)

Use this command to process a list of files using multiple CPU cores via MPI.

**Step 1: Create a file list**
Create a text file containing the paths to your FITS images (one per line).
```bash
# Correct way to generate list (Absolute paths recommended)
find /data/raw -name "*.fits" > filelist.txt
```
*> **Warning:** Do not use `cat *.fits > filelist`. This will write binary data to the text file and crash the program.*

**Step 2: Run with `mpirun`**
```bash
# Syntax: mpirun -np <N_CORES> hpastrometry-mpi <filelist> <output_dir> <suffix>

mpirun -np 4 hpastrometry-mpi filelist.txt ./output_dir _refined
```

**Explanation:**
*   `-np 4`: Use 4 processor cores.
*   `filelist.txt`: The text file created in Step 1.
*   `./output_dir`: Where results will be saved.
*   `_refined`: Suffix for output files. `image.fits` -> `image_refined.fits`.

---

## 🐍 Python API

You can also use the pipeline directly within your own Python scripts:

```python
from hpastrometry.astrometry import run_hpastrometry

run_hpastrometry(
    infile="data/raw_image.fits",
    outfile="data/processed_image.fits",
    verbose=True,
    enforce_scamponlinecatalog='GAIA-DR3',
    enforce_checkprior=True # Attempts to read RA/DEC from header first
)
```

---

## ⚙️ How it Works

1.  **WCS Strip**: Existing WCS headers are removed to ensure a fresh solution.
2.  **Prior Check**: The code looks for RA/DEC keywords in the header to narrow the search (optional).
3.  **Coarse Solve**: `solve-field` (Astrometry.net) runs on a downsampled image to find a rough WCS.
4.  **Source Extraction**: `sextractor` generates a clean source catalog from the solved image.
5.  **Refinement**: `scamp` matches the source catalog against an online reference (e.g., Gaia) to calculate distortion coefficients.
6.  **Integration**: The refined SCAMP header (`.head`) is merged back into the original image.

---

## ❓ Troubleshooting

**Q: I see `RuntimeWarning: suspicious MPI execution environment`**
*   **Cause:** Mismatch between the MPI library used by `mpirun` (e.g., Intel MPI or MPICH) and the one `mpi4py` was built against (usually OpenMPI).
*   **Fix:** If using Anaconda, run `conda install mpi4py`. If using system Python, ensure you compile `mpi4py` using your system's `mpicc`.

**Q: The code crashes with `UnicodeDecodeError` in MPI mode.**
*   **Cause:** Your input file list likely contains binary characters.
*   **Fix:** Check your file list (`head filelist.txt`). Did you accidentally run `cat *.fits > filelist`? Regenerate it using `ls *.fits > filelist`.

**Q: "Command not found" errors.**
*   **Cause:** The external tools are not in your path.
*   **Fix:** Ensure you can run `scamp` and `solve-field` in your terminal before running this pipeline.

---

## License

[MIT License](LICENSE)
