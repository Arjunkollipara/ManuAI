# Clean Python 3.11 Recovery and Full Validation

Timestamp: 2026-05-07 02:13:30 IST

Goal: diagnose Python 3.11 MSI failure, attempt the safest recovery without damaging Python 3.14, then prove or disprove Python 3.11 reproducibility for Azure/Docker readiness.

Final verdict: NOT REPRODUCIBLE

## Python 3.11 Installer Failure Diagnosis

Initial launcher state:

```text
> py -0p
No installed Pythons found!

> py -3.11 --version
No installed Python found!
```

Python launcher binary:

```text
C:\Users\arjun\AppData\Local\Programs\Python\Launcher\py.exe
Version: 3.14.4150.1013
```

Existing install directory check:

```text
C:\Users\arjun\AppData\Local\Programs\Python\Python311 existed
```

But `python.exe` was absent:

```text
> Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python311" -Recurse -Filter python*.exe
<no results>
```

Registry checks:

```text
> reg query HKCU\Software\Python /s
ERROR: The system was unable to find the specified registry key or value.
```

HKLM contained broken Python 3.11 entries pointing to a missing machine-wide path:

```text
HKLM\Software\Python\PythonCore\3.11\Help\Main Python Documentation
    (Default)    REG_SZ    C:\Program Files\Python311\Doc\html\index.html

HKLM\Software\Python\PythonCore\3.11\PythonPath
    (Default)    REG_SZ    C:\Program Files\Python311\Lib\;C:\Program Files\Python311\DLLs\
```

But `C:\Program Files\Python311` does not exist.

Windows Installer evidence:

```text
Product: Python 3.11.9 Core Interpreter (64-bit) -- Error 1334.
The file 'python.dll' cannot be installed because the file cannot be found in cabinet file 'cab1.cab'.
Installation success or error status: 1603.
```

The same Error 1334/1603 pattern was observed for Python 3.11.0, 3.11.3, and freshly downloaded Python 3.11.9 MSI bundle attempts.

Other checks:

- `msiserver` was running.
- A stale/idle `msiexec` process was observed.
- Python directory ACL allowed the user full control.
- Installer software restriction policy allowed the signed MSI.
- No direct Access Denied failure was found in the MSI log.
- Defender status query returned no useful output in this shell.

Diagnosis:

The failed Python 3.11 install is not primarily a project issue. It is a Windows Installer/MSI payload failure during `core_JustForMe`: the core MSI cannot find `python.dll` in `cab1.cab`. The system also had broken Python 3.11 registry remnants under HKLM pointing to `C:\Program Files\Python311`, while the attempted install target was per-user under AppData. The Python launcher could not detect 3.11 because no valid HKCU PythonCore registration existed and the HKLM entry was incomplete/broken.

## Remediation Plan

Safest recovery plan selected:

1. Do not modify Python 3.14.
2. Do not delete machine-wide HKLM Python registry keys without admin cleanup approval.
3. Back up the partial per-user `Python311` directory.
4. Download a fresh official Python 3.11.9 installer and try a per-user install with PATH and launcher changes disabled.
5. If MSI still fails, use an MSI-free official Python 3.11.9 NuGet runtime as a recovery runtime.
6. Register only HKCU `Software\Python\PythonCore\3.11` so the existing launcher can detect 3.11.
7. Validate `py -3.11`, create a clean venv, and run the full project validation.

## Recovery Actions Performed

Backed up partial Python311:

```text
Backed up partial Python311 to Python311.broken_20260507_020955
```

Downloaded fresh Python 3.11.9 installer:

```text
reports\python-3.11.9-amd64.exe
Signature: Valid
```

Per-user installer command:

```text
python-3.11.9-amd64.exe /quiet InstallAllUsers=0 TargetDir=C:\Users\arjun\AppData\Local\Programs\Python\Python311 PrependPath=0 Include_launcher=0 Include_pip=1 Include_test=0 Include_doc=0 Include_tcltk=1 /log reports\python311_recovery_install_20260507_020955.log
```

Result:

```text
ExitCode=1603
```

Fresh installer failure:

```text
Error 0x80070643: Failed to install MSI package.
Product: Python 3.11.9 Core Interpreter (64-bit) -- Error 1334.
The file 'python.dll' cannot be installed because the file cannot be found in cabinet file 'cab1.cab'.
```

MSI-free recovery:

```text
Downloaded: reports\python.3.11.9.nupkg
Extracted: reports\python_nuget_3_11_9\tools
```

NuGet runtime verification:

```text
> reports\python_nuget_3_11_9\tools\python.exe --version
Python 3.11.9

> python.exe -c "import sys, ensurepip, venv; ..."
ensurepip ok
venv ok
```

Copied verified runtime to:

```text
C:\Users\arjun\AppData\Local\Programs\Python\Python311
```

Registered HKCU PythonCore 3.11:

```text
HKCU\Software\Python\PythonCore\3.11
    SysVersion    REG_SZ    3.11
    Version       REG_SZ    3.11.9
    DisplayName   REG_SZ    Python 3.11.9 (NuGet runtime recovery)

HKCU\Software\Python\PythonCore\3.11\InstallPath
    (Default)                C:\Users\arjun\AppData\Local\Programs\Python\Python311\
    ExecutablePath           C:\Users\arjun\AppData\Local\Programs\Python\Python311\python.exe
    WindowedExecutablePath   C:\Users\arjun\AppData\Local\Programs\Python\Python311\pythonw.exe
```

Recovered launcher verification:

```text
> py -0p
 -V:3.11 *        C:\Users\arjun\AppData\Local\Programs\Python\Python311\python.exe

> py -3.11 --version
Python 3.11.9
```

Python 3.14 was not modified by the recovery steps.

## Python Runtime Validation

Final Python 3.11 launcher validation succeeded:

```text
> py -0p
 -V:3.11 *        C:\Users\arjun\AppData\Local\Programs\Python\Python311\python.exe

> py -3.11 --version
Python 3.11.9
```

Clean environment creation:

```text
> py -3.11 -m venv env311_validation
```

Venv interpreter:

```text
> .\env311_validation\Scripts\python.exe --version
Python 3.11.9

> .\env311_validation\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
C:\Users\arjun\Desktop\manufatoring_analysis_predictions\manufacturing-suite\env311_validation\Scripts\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
```

Activation via `cmd`:

```text
> cmd /c "env311_validation\Scripts\activate.bat && python --version && python -c ""import sys; print(sys.executable)"""
Python 3.11.9
C:\Users\arjun\Desktop\manufatoring_analysis_predictions\manufacturing-suite\env311_validation\Scripts\python.exe
```

## Dependency Installation Results

Installer tooling upgrade:

```text
> .\env311_validation\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
Successfully installed packaging-26.2 pip-26.1.1 setuptools-82.0.1 wheel-0.47.0
WARNING: Cache entry deserialization failed, entry ignored
```

Proposed lock install:

```text
> .\env311_validation\Scripts\python.exe -m pip install -r reports\requirements.lock.proposed_20260507_010000.txt
```

Result:

```text
The conflict is caused by:
    The user requested packaging==26.2
    langchain-core 0.1.53 depends on packaging<24.0 and >=23.2

ERROR: Cannot install -r reports\requirements.lock.proposed_20260507_010000.txt (line 45) and packaging==26.2 because these package versions have conflicting dependencies.
ERROR: ResolutionImpossible
```

No compilation failure occurred. The dependency stage failed at resolver conflict before application packages were installed.

## pip check Results

```text
> .\env311_validation\Scripts\python.exe -m pip check
No broken requirements found.

> .\env311_validation\Scripts\python.exe -m pip freeze
packaging==26.2
```

This confirms only the mostly empty venv is internally consistent. It does not validate the application lock.

## Import Validation Results

All required imports were attempted. All failed because dependency installation did not complete.

Representative failures:

```text
api.main -> ModuleNotFoundError: No module named 'fastapi'
api.database.connection -> ModuleNotFoundError: No module named 'sqlalchemy'
ml.train -> ModuleNotFoundError: No module named 'pandas'
pipeline.ingest -> ModuleNotFoundError: No module named 'pandas'
rag.embeddings -> ModuleNotFoundError: No module named 'langchain_community'
rag.vector_store -> ModuleNotFoundError: No module named 'langchain_chroma'
agents.crew -> ModuleNotFoundError: No module named 'langchain_openai'
agents.maintenance_agent -> ModuleNotFoundError: No module named 'langchain_chroma'
agents.analytics_agent -> ModuleNotFoundError: No module named 'sqlalchemy'
agents.ml_insight_agent -> ModuleNotFoundError: No module named 'pandas'
```

No deprecation warnings were reached.

## Pipeline Validation Results

Commands executed:

```text
> python download_data.py
ModuleNotFoundError: No module named 'pandas'

> python pipeline\ingest.py
ModuleNotFoundError: No module named 'pandas'

> python pipeline\transform.py
ModuleNotFoundError: No module named 'pandas'

> python pipeline\feature_engineer.py
ModuleNotFoundError: No module named 'pandas'

> python pipeline\validate.py
ModuleNotFoundError: No module named 'pandas'
```

Parquet generation: not reached.

Validation reports: not generated.

Metadata generation: not generated.

Logs creation: not validated because imports failed.

## ML Validation Results

Commands executed:

```text
> python ml\train.py
ModuleNotFoundError: No module named 'pandas'

> python ml\evaluate.py
ModuleNotFoundError: No module named 'pandas'
```

Model generation: not reached.

Metrics:

- accuracy: not available
- precision: not available
- recall: not available
- f1: not available
- roc_auc: not available

No WinError parallelization failures were observed because training never reached sklearn/joblib.

## RAG Validation Results

RAG validation was attempted with embedding, vector store, and retrieval paths:

```text
RAG validation start
embeddings FAIL
vector_store FAIL
retriever/query FAIL

ModuleNotFoundError: No module named 'langchain_community'
ModuleNotFoundError: No module named 'langchain_chroma'
```

Embedding model loading: not reached.

ChromaDB initialization: not reached.

Vector persistence: not reached.

Real retrieval query: attempted but not executed due import failure.

Chunk counts: not available.

Source attribution: not available.

## API Runtime Results

FastAPI startup command:

```text
> python -m uvicorn api.main:app --host 127.0.0.1 --port 8010
C:\Users\arjun\Desktop\manufatoring_analysis_predictions\manufacturing-suite\env311_validation\Scripts\python.exe: No module named uvicorn
```

Endpoint probes:

- GET `/`: not reached.
- GET `/health`: not reached.
- GET `/docs`: not reached.
- GET `/system/config`: not reached.

Startup success: no.

Model loading: not reached.

DB connection: not reached.

## CrewAI Runtime Results

CrewAI construction was attempted:

```text
CrewAI runtime validation start
CrewAI direct construction FAIL
ModuleNotFoundError: No module named 'crewai'

project agents.crew import FAIL
ModuleNotFoundError: No module named 'langchain_openai'
```

Agent construction: not reached.

Crew construction: not reached.

Tool registration: not reached.

Azure credential handling: not reached.

## Test Suite Results

Command executed:

```text
> python -m pytest tests -v
C:\Users\arjun\Desktop\manufatoring_analysis_predictions\manufacturing-suite\env311_validation\Scripts\python.exe: No module named pytest
```

Passed tests: 0.

Failed tests: not collected.

Warnings: none reached.

## Blocking Issues

1. Standard Python 3.11 MSI installation still fails with Error 1334 / 1603 / 0x80070643 during `core_JustForMe`.
2. HKLM contains broken Python 3.11 registry remnants pointing to missing `C:\Program Files\Python311`.
3. Python 3.11 launcher recovery succeeded only through an MSI-free NuGet runtime plus HKCU registration, not through the normal Python installer.
4. The proposed dependency lock is unsatisfiable: `packaging==26.2` conflicts with `langchain-core==0.1.53`, which requires `packaging>=23.2,<24.0`.
5. Because the lock does not install, all runtime validations fail downstream due missing dependencies.

## Non-Blocking Warnings

1. `pip install --upgrade pip setuptools wheel` emitted `WARNING: Cache entry deserialization failed, entry ignored`.
2. `pip check` is clean only because the lock did not install the application graph.
3. `where python` under `cmd` activation returned no result even though `python --version` and `sys.executable` correctly resolved to the venv Python.
4. Defender/antivirus status could not be usefully captured from this shell; no explicit antivirus block was found in MSI logs.

## Azure Migration Readiness

Not ready.

Python 3.11 can now be invoked through `py -3.11`, and a clean Python 3.11 venv can be created. However, the proposed dependency lock cannot be installed, so the application cannot be reproduced for Azure/Docker readiness. API, ML, RAG, CrewAI, and tests are blocked by dependency resolution.

## Final Stability Score (0-100)

35

Python 3.11 launcher and venv creation were recovered, but the official MSI path remains broken and the application dependency lock is not reproducible.

## Final Verdict

NOT REPRODUCIBLE
