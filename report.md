# Manufacturing Quality & Productivity Suite - Project Report

Generated on: 2026-05-06

## 1. Plain-English Summary

This project is an end-to-end manufacturing intelligence system. Its main job is to help a factory understand machine health, predict possible machine failures, store sensor readings, create alerts, search maintenance documents, and answer operational questions using AI agents.

In simple terms, the project does five big things:

1. It collects or loads manufacturing machine data.
2. It cleans the data and prepares it for analysis.
3. It trains a machine learning model that predicts whether a machine is likely to fail.
4. It exposes the model through an API so other software can send sensor readings and receive predictions.
5. It adds document search and AI-agent support so users can ask maintenance or analytics questions in plain language.

The current project is not only a code skeleton. It already contains:

- A working FastAPI backend.
- A SQLite database file.
- A trained Random Forest machine learning model.
- Data files in raw, staged, and curated formats.
- Data quality and validation reports.
- Prediction APIs.
- Sensor ingestion APIs.
- Alert creation logic.
- RAG document search over maintenance SOP text files.
- CrewAI-based agent routing.
- Tests for the data pipeline, model, and API.
- Docker and Docker Compose deployment support.
- Azure deployment configuration placeholders.
- A GitHub Actions workflow for testing and building.

## 2. What Problem This Project Solves

Manufacturing machines produce readings such as temperature, speed, torque, and tool wear. These readings can reveal whether a machine is behaving normally or moving toward failure.

Without software like this, a factory team might only react after a breakdown happens. This project supports a more proactive approach:

- It looks at machine sensor values.
- It estimates the probability of machine failure.
- It labels the risk as LOW, MEDIUM, HIGH, or CRITICAL.
- It stores the prediction history.
- It creates alerts when risk is high.
- It helps technicians search procedures such as overheating diagnosis or bearing replacement.
- It gives AI agents tools to explain predictions and answer maintenance or production questions.

## 3. Main Technologies Used

The project uses Python and several specialized libraries:

- FastAPI: Builds the web API.
- Uvicorn: Runs the FastAPI server.
- Pydantic: Validates request and response data.
- SQLAlchemy: Talks to the database.
- SQLite: Local development database, stored in `manufacturing.db`.
- Pandas: Loads, cleans, and transforms tabular data.
- PyArrow: Reads and writes Parquet files.
- Scikit-learn: Trains and evaluates the machine learning model.
- ChromaDB: Stores searchable document embeddings locally.
- LangChain: Supports embeddings and vector retrieval.
- CrewAI: Defines and orchestrates AI agents.
- Azure OpenAI: Intended LLM provider for production or configured environments.
- Azure AI Search: Intended production search service.
- Pytest: Runs automated tests.
- Docker: Packages the API into a container.
- GitHub Actions: Runs CI steps.

## 4. Current Project Structure

At the root level, the project contains these important areas:

- `.github/`: GitHub Actions automation.
- `agents/`: AI agent definitions and orchestration logic.
- `api/`: FastAPI application, routes, database connection, data schemas, and API models.
- `dashboard/`: Placeholder for a future dashboard.
- `data/`: Raw, staged, curated, and vector-store data.
- `deployment/`: Azure deployment notes and configuration.
- `documents/`: Maintenance and SOP text documents used for search.
- `logs/`: Log files written by pipeline, ML, and API processes.
- `ml/`: Model training, evaluation, and prediction code.
- `pipeline/`: Data ingestion, cleaning, feature engineering, and validation code.
- `rag/`: Retrieval-augmented generation document search code.
- `tests/`: Automated tests.
- `Dockerfile`: Container build instructions.
- `docker-compose.yml`: Local container run configuration.
- `requirements.txt`: Python dependency list.
- `README.md`: Short project overview.
- `CONTEXT.md`: Project purpose, stack, phases, and known issues.
- `manufacturing.db`: Local SQLite database.

## 5. Data Journey Through the Project

The project follows a clear data path:

1. Raw data starts in `data/raw/ai4i2020.csv`.
2. The ingestion script validates the CSV and saves `data/raw/ai4i2020.parquet`.
3. The transformation script standardizes column names, removes duplicates, fills missing values, checks ranges, and saves `data/staged/ai4i2020_staged.parquet`.
4. The feature engineering script creates machine-learning-ready features and saves:
   - `data/curated/ai4i2020_curated.parquet`
   - `data/curated/ai4i2020_features.parquet`
   - `data/curated/feature_metadata.json`
5. The validation script checks that all required data files exist and are consistent, then saves `data/curated/validation_report.json`.
6. The training script trains a Random Forest model and saves:
   - `ml/models/random_forest.pkl`
   - `ml/models/training_metadata.json`
7. The evaluation script checks model performance and saves `ml/models/evaluation_report.json`.
8. The API uses the saved model to make predictions for new sensor readings.

## 6. Data Quality Results

The staged quality report says:

- Total rows: 10,000.
- Duplicate rows removed: 0.
- Missing values filled: none.
- Range violations: 0 for all monitored numeric fields.
- Flagged rows: 0.
- Clean rows: 10,000.
- Validation status: PASSED.

The curated validation report says:

- All required files exist.
- Raw, staged, and curated data all contain 10,000 rows.
- Feature completeness passed.
- Target integrity passed.
- Machine failure rate is 3.39%.
- Feature sanity passed.
- Log integrity passed.
- Overall status: PASSED.
- Ready for machine learning: true.

For a non-technical reader: this means the project successfully prepared a clean dataset, and the dataset is considered good enough to train the model.

## 7. Machine Learning Model

The project trains a Random Forest classifier. A Random Forest is a machine learning method that makes many decision trees and combines their answers. It is often used when data has several numeric measurements and the goal is to classify something, such as "failure" or "no failure."

The model predicts the target field:

- `machine_failure`: 0 means no failure, 1 means failure.

The model uses 13 input features:

- `air_temp_k`: Air temperature in Kelvin.
- `process_temp_k`: Process temperature in Kelvin.
- `rotational_speed_rpm`: Machine rotational speed.
- `torque_nm`: Torque/load on the machine.
- `tool_wear_min`: Tool wear time in minutes.
- `temp_difference`: Difference between process temperature and air temperature.
- `power`: Torque multiplied by rotational speed.
- `tool_wear_rate`: Tool wear relative to machine speed.
- `temp_wear_interaction`: Temperature multiplied by wear.
- `high_torque_flag`: 1 if torque is above 60 Nm, otherwise 0.
- `high_wear_flag`: 1 if tool wear is above 200 minutes, otherwise 0.
- `type_encoded`: Machine/product type converted from L, M, H into numbers.
- `failure_risk_score`: A manually calculated risk score from torque, wear, temperature difference, and high-risk flags.

### Training Results

The saved training metadata shows:

- Model type: RandomForestClassifier.
- Training rows: 8,000.
- Test rows: 2,000.
- Accuracy: 98.7%.
- Precision: 82.81%.
- Recall: 77.94%.
- F1 score: 80.30%.
- ROC AUC: 96.97%.

Plain-English meaning:

- Accuracy tells how often the model is correct overall.
- Precision tells how often predicted failures are truly failures.
- Recall tells how many real failures the model catches.
- F1 score balances precision and recall.
- ROC AUC measures how well the model separates failure cases from non-failure cases.

The current model meets the code's target thresholds:

- Recall is above 70%.
- F1 score is above 50%.
- ROC AUC is above 85%.

### Full Evaluation Results

The evaluation report over the full feature dataset shows:

- Rows evaluated: 10,000.
- Accuracy: 99.6%.
- Precision: 93.59%.
- Recall: 94.69%.
- F1 score: 94.13%.
- ROC AUC: 99.41%.

The most important features are:

- `rotational_speed_rpm`
- `torque_nm`
- `power`
- `temp_difference`
- `failure_risk_score`

Plain-English meaning: speed, load, calculated power, temperature gap, and risk score are the strongest signals for predicting failures.

## 8. API Overview

The API is built with FastAPI and starts in `api/main.py`.

When the application starts, it:

- Loads and validates environment settings.
- Logs whether Azure OpenAI and Azure Search are configured.
- Creates database tables if they do not already exist.
- Loads the machine learning predictor.
- Registers API route groups.

The root endpoint `/` returns a welcome message and points users to `/docs` and `/health`.

The health endpoint `/health` returns:

- Whether the API is healthy.
- API version.
- Whether the model is loaded.
- Database status.
- Current timestamp.

The system config endpoint `/system/config` returns environment readiness information, with secrets masked or omitted from direct exposure.

## 9. API Routes

### Ingestion Routes

These routes live in `api/routes/ingest.py`.

`POST /ingest/sensor-data`

- Accepts one machine sensor reading.
- Runs a model prediction immediately.
- Saves the sensor reading to the database.
- Saves the prediction to the database.
- Creates an alert if the risk level is HIGH or CRITICAL.
- Returns the saved sensor ID and alert status.

`GET /ingest/sensor-data`

- Returns recent sensor readings.
- Supports pagination with `limit` and `offset`.

`GET /ingest/sensor-data/{sensor_id}`

- Returns one sensor reading by database ID.
- Returns 404 if the reading does not exist.

`GET /ingest/stats`

- Returns total readings, total alerts, failure rate, high-risk count, critical-risk count, and last ingestion time.

### Prediction Routes

These routes live in `api/routes/predict.py`.

`POST /predict/failure`

- Accepts sensor data inside a prediction request.
- Runs the trained model.
- Optionally saves the prediction to the database.
- Creates an alert if the model predicts failure.
- Returns probability, risk level, explanation, and top contributing features.

`GET /predict/history`

- Returns prediction history from the database.
- Supports pagination.

`GET /predict/history/{prediction_id}`

- Returns one prediction record.
- Returns 404 if it cannot find that record.

`POST /predict/batch`

- Accepts multiple sensor readings.
- Runs predictions for all readings.
- Does not save the batch results to the database.
- Limits the batch to 50 readings.

`GET /predict/alerts`

- Returns alerts.
- Can filter by resolved status or severity.

### Search Routes

These routes live in `api/routes/search.py`.

`GET /search/documents`

- Searches the maintenance documents.
- Uses the RAG pipeline and ChromaDB vector store.
- Returns matching text chunks, source file names, relevance scores, and formatted context.

`GET /search/documents/health`

- Checks whether the RAG document search is initialized.
- Returns vector store type and number of indexed documents.

### Agent Routes

These routes live in `api/routes/agent.py`.

`POST /agent/query`

- Accepts a plain-language question.
- Sends it to the agent orchestration layer.
- Returns the answer, which agent was used, sources, status, and timestamp.

`GET /agent/status`

- Reports whether agent credentials are configured.
- Lists available agents:
  - MaintenanceAgent
  - AnalyticsAgent
  - MLInsightAgent

## 10. Database Design

The database connection is managed by `api/database/connection.py`.

By default, the project uses:

- `sqlite:///./manufacturing.db`

That means local data is stored in the root-level file `manufacturing.db`.

The database tables are defined in `api/database/schemas.py`.

### `sensor_readings`

Stores actual or submitted machine readings:

- ID.
- UDI.
- Product ID.
- Type.
- Air temperature.
- Process temperature.
- Rotational speed.
- Torque.
- Tool wear.
- Machine failure value.
- Creation timestamp.

### `prediction_records`

Stores model predictions:

- ID.
- Optional link to a sensor reading.
- Whether failure was predicted.
- Failure probability.
- Risk level.
- Explanation.
- Top features.
- Creation timestamp.

### `alert_records`

Stores alerts created from risky predictions:

- ID.
- Prediction ID.
- Machine ID.
- Alert type.
- Severity.
- Message.
- Whether it is resolved.
- Creation timestamp.

### `maintenance_logs`

Stores future maintenance notes:

- ID.
- Machine ID.
- Action taken.
- Technician notes.
- Creation timestamp.

## 11. Input Validation

The API uses Pydantic models to validate incoming data.

`api/models/sensor.py` defines the required sensor input:

- `type` must be one of L, M, or H.
- `air_temp_k` must be from 290 to 320.
- `process_temp_k` must be from 300 to 330.
- `rotational_speed_rpm` must be from 500 to 3000.
- `torque_nm` must be from 0 to 100.
- `tool_wear_min` must be from 0 to 300.

This protects the system from obviously invalid sensor readings.

`api/models/prediction.py` defines request and response shapes for predictions and alerts.

## 12. RAG and Document Search

RAG means retrieval-augmented generation. In this project, it means the system can search maintenance documents and provide relevant source text to agents or API users.

The RAG code is in the `rag/` folder.

### `rag/embeddings.py`

This file:

- Loads the local Hugging Face embedding model `all-MiniLM-L6-v2`.
- Splits documents into overlapping text chunks.
- Reads document files safely.

Embeddings are numerical representations of text. They let the system find text with similar meaning, not just exact matching words.

### `rag/vector_store.py`

This file:

- Builds a ChromaDB vector store from `.txt` documents.
- Saves the vector store under `data/vector_store/`.
- Loads the existing vector store when possible.
- Can switch to Azure AI Search in production if Azure credentials are configured.

### `rag/retriever.py`

This file:

- Runs similarity search.
- Formats results with source names and relevance scores.
- Returns API-ready search results.

## 13. Maintenance Documents

The `documents/` folder contains text files used by the RAG search system.

`documents/predictive_maintenance_guide.txt`

- Explains predictive maintenance, sensor interpretation, thresholds, trend analysis, risk levels, and maintenance recordkeeping.

`documents/overheating_diagnosis_sop.txt`

- Explains safe diagnosis of overheating in motors, compressors, pumps, turbines, and drive systems.
- Includes temperature thresholds, emergency response guidance, diagnostic steps, cooling checks, preventive measures, and documentation requirements.

`documents/bearing_maintenance_sop.txt`

- Explains bearing inspection and replacement.
- Includes safety warnings, tools required, inspection steps, replacement steps, post-maintenance checks, and escalation criteria.

`documents/sample_sop.txt`

- Placeholder sample SOP content.

## 14. AI Agents

The `agents/` folder defines AI-assisted roles.

These agents require Azure OpenAI credentials to actually run language-model responses.

### `agents/crew.py`

This is the orchestration layer.

It:

- Creates the Azure OpenAI LLM client.
- Checks whether Azure OpenAI credentials exist.
- Routes questions to the right agent type.
- Runs a single agent for simple questions.
- Runs multiple agents for questions needing both diagnosis and repair guidance.

The router looks for keywords:

- Maintenance questions go to the maintenance agent.
- Production, trend, and statistics questions go to the analytics agent.
- Prediction, risk, model, and feature questions go to the ML insight agent.

### `agents/maintenance_agent.py`

This agent acts like a senior maintenance technician.

It has a tool called `search_maintenance_manuals`, which searches SOPs and maintenance documents using the RAG pipeline.

### `agents/analytics_agent.py`

This agent acts like a manufacturing analytics specialist.

It has tools to:

- Get production statistics from the database.
- Get recent alerts from the database.

### `agents/ml_insight_agent.py`

This agent acts like an ML systems analyst.

It has tools to:

- Get model feature importance.
- Predict failure risk from sensor JSON.

## 15. Pipeline Files

### `download_data.py`

This script tries to download the AI4I 2020 predictive maintenance dataset from the UCI Machine Learning Repository.

If downloading fails, it creates synthetic data with similar columns. This makes the project more resilient because development can continue even without internet access.

### `pipeline/ingest.py`

This script:

- Loads the raw CSV.
- Checks that required columns exist.
- Checks that there is at least one row.
- Checks that there are no fully empty rows.
- Saves the validated raw data as Parquet.
- Writes progress to `logs/pipeline.log`.

### `pipeline/transform.py`

This script:

- Loads the raw Parquet file.
- Removes fully duplicate rows.
- Renames columns into code-friendly names.
- Fills missing values.
- Checks important numeric ranges.
- Adds a `data_quality_flag`.
- Saves the staged dataset.
- Saves the quality report.

### `pipeline/feature_engineer.py`

This script:

- Loads staged data.
- Creates 13 machine learning features.
- Saves the full curated dataset.
- Saves the feature-only dataset.
- Saves feature metadata.

### `pipeline/validate.py`

This script:

- Confirms required files exist.
- Confirms row counts are consistent.
- Confirms expected features are present.
- Confirms the target column is valid.
- Checks feature sanity.
- Checks that pipeline logs contain expected stage mentions.
- Writes a validation report.

## 16. ML Files

### `ml/train.py`

This file:

- Loads curated feature data.
- Splits data into training and testing portions.
- Trains a Random Forest classifier.
- Evaluates the model.
- Saves the trained model.
- Saves training metadata.
- Checks whether performance targets are met.

### `ml/evaluate.py`

This file:

- Loads the saved model.
- Evaluates predictions against labeled data.
- Calculates accuracy, precision, recall, F1, ROC AUC, confusion matrix, and classification report.
- Extracts feature importance.
- Explains a single prediction by risk level and top contributing features.
- Saves a full evaluation report.

### `ml/predict.py`

This file:

- Loads the trained model once and reuses it through a singleton.
- Converts raw sensor readings into the same 13 features used during training.
- Validates required input keys.
- Computes derived features.
- Runs model prediction.
- Returns failure prediction, probability, risk level, top contributing features, explanation, original input, and timestamp.
- Supports batch predictions by running the same prediction flow repeatedly.

## 17. Logs

The project writes logs to:

- `logs/pipeline.log`: Data pipeline activity.
- `logs/ml.log`: Model training, evaluation, and prediction activity.
- `logs/api.log`: API startup and route activity.

These logs help developers and operators understand what happened, when it happened, and where failures occurred.

## 18. Tests

Automated tests are in the `tests/` folder.

### `tests/conftest.py`

This file prepares the test environment by:

- Adding the project root to Python's import path.
- Changing the working directory to the project root.

### `tests/test_pipeline.py`

These tests check:

- Raw data file exists.
- Raw data has the required schema.
- Staged data exists.
- Staged data has no null values.
- Staged data includes `data_quality_flag`.
- Curated feature data and metadata exist.
- Engineered feature values are calculated correctly.
- Validation report passed.

### `tests/test_ml.py`

These tests check:

- Model file exists.
- Training metadata exists.
- Model loads correctly.
- Model has prediction methods.
- Training metrics meet minimum targets.
- Predictor singleton works.
- Preprocessing creates exactly 13 features.
- Prediction output has required fields.
- High-risk input produces higher probability than normal input.
- Feature importance values are valid and sum close to 1.

### `tests/test_api.py`

These tests check:

- Health endpoint.
- Root endpoint.
- Sensor ingestion.
- Alert creation for high-risk input.
- Reading stored sensor data.
- Looking up sensor readings by ID.
- 404 behavior for missing sensor readings.
- Prediction endpoint.
- High-risk prediction behavior.
- Search endpoint.
- Agent status endpoint.
- Agent query fallback.
- System configuration endpoint.
- API validation for bad input.
- Batch prediction endpoint.

## 19. Deployment and Operations

### `Dockerfile`

The Dockerfile:

- Uses Python 3.11 slim.
- Installs system dependencies such as compilers and curl.
- Installs Python dependencies.
- Copies project files into the container.
- Creates required folders.
- Exposes port 8000.
- Adds a health check against `/health`.
- Starts the API using Uvicorn.

### `docker-compose.yml`

Docker Compose defines one service:

- `api`, container name `manufacturing-api`.

It:

- Builds from the current project.
- Maps local port 8000 to container port 8000.
- Sets environment variables.
- Mounts data, logs, model files, and documents as volumes.
- Restarts unless stopped.
- Uses `/health` as a health check.

### `deployment/azure_config.yml`

This file outlines intended Azure production resources:

- Azure App Service for the FastAPI app.
- Azure SQL Database for production data.
- Azure OpenAI for language model responses.
- Azure AI Search for production document retrieval.
- Azure Key Vault for secrets.

### `deployment/deployment_diagram.md`

This file describes the intended production architecture:

- Users access FastAPI through Azure App Service.
- FastAPI talks to Azure SQL, Azure OpenAI, and Azure AI Search.
- Azure Key Vault stores secrets.
- ChromaDB is used for local development.
- GitHub Actions is intended for CI/CD.
- Power BI is planned for dashboards/reporting.

Note: The diagram currently displays some box-drawing characters incorrectly, likely due to text encoding issues. The meaning is still clear, but the visual formatting could be cleaned up later.

### `.github/workflows/deploy.yml`

This GitHub Actions workflow:

- Runs on pushes and pull requests to `main`.
- Sets up Python 3.11.
- Installs dependencies.
- Runs the pipeline scripts.
- Trains the model.
- Runs tests.
- Initializes RAG.
- Builds a Docker image on `main`.
- Leaves actual Azure deployment commented out until Azure is configured.

## 20. Environment and Security

`api/security.py` reads environment variables and checks readiness.

Important environment variables include:

- Azure OpenAI key and endpoint.
- Azure OpenAI deployment and API version.
- Database URL.
- Azure SQL connection string.
- Azure AI Search key, endpoint, and index.
- Azure Key Vault URL.
- Azure client credentials.
- Environment name.
- Log level.
- API version.

Sensitive values are masked in logs:

- Azure OpenAI key.
- Azure SQL connection string.
- Azure AI Search key.
- Azure client secret.

In development, the system can run with local SQLite and local ChromaDB.

In production, the project expects stronger Azure configuration, including Azure SQL, Azure AI Search, Azure OpenAI, and Key Vault.

## 21. Generated Artifacts

The project includes generated files, not just source code.

Important generated artifacts:

- `data/raw/ai4i2020.csv`: Source dataset.
- `data/raw/ai4i2020.parquet`: Validated raw data.
- `data/staged/ai4i2020_staged.parquet`: Cleaned staged data.
- `data/staged/quality_report.json`: Data quality report.
- `data/curated/ai4i2020_curated.parquet`: Curated data with engineered features.
- `data/curated/ai4i2020_features.parquet`: Model-ready features.
- `data/curated/feature_metadata.json`: Feature list and statistics.
- `data/curated/validation_report.json`: Pipeline validation report.
- `data/vector_store/`: ChromaDB vector store for document search.
- `ml/models/random_forest.pkl`: Trained model.
- `ml/models/training_metadata.json`: Training results.
- `ml/models/evaluation_report.json`: Full evaluation results.
- `manufacturing.db`: Local API database.

## 22. What Has Been Completed

The following work appears completed or mostly completed:

- Project folder structure created.
- Core Python dependencies listed.
- Raw data acquisition script created.
- Data ingestion implemented.
- Data transformation implemented.
- Feature engineering implemented.
- Data validation implemented.
- Clean data artifacts generated.
- Validation report generated and passing.
- Random Forest model trained.
- Model saved to disk.
- Training metadata saved.
- Full model evaluation saved.
- Prediction logic implemented.
- Prediction explanations implemented.
- FastAPI app implemented.
- Database connection implemented.
- Database table schemas implemented.
- Input validation implemented.
- Sensor ingestion endpoint implemented.
- Prediction endpoints implemented.
- Alert endpoints implemented.
- Search endpoints implemented.
- Agent endpoints implemented.
- Local RAG document search implemented.
- Maintenance SOP documents added.
- Agent classes and tools added.
- Tests added for pipeline, ML, and API behavior.
- Dockerfile added.
- Docker Compose file added.
- Azure configuration draft added.
- GitHub Actions workflow added.
- Logging added across pipeline, ML, and API layers.

## 23. What Is Still Incomplete or Needs Attention

The project is strong, but several areas are still incomplete or could be improved:

- `README.md` is very short and still says setup instructions are "to be added".
- `dashboard/` only contains `.gitkeep`; no dashboard has been built yet.
- Azure deployment is planned but not fully active.
- GitHub Actions has the deploy job commented out.
- `deployment/deployment_diagram.md` has encoding issues in its diagram characters.
- `documents/sample_sop.txt` is only placeholder text.
- There is no authentication or role-based access control on API endpoints.
- CORS currently allows all origins, which is convenient for development but too open for production.
- Agent answers require Azure OpenAI credentials.
- Production-grade secret handling is described, but runtime integration with Key Vault is not fully implemented in code.
- The API uses SQLite by default; production should use a managed database such as Azure SQL.
- Alerts can be created and read, but there is no endpoint yet to mark alerts as resolved.
- Maintenance logs table exists, but there are no API routes yet to create or view maintenance logs.
- The model is trained on AI4I/synthetic-style data, not necessarily real factory data from this user's environment.
- The project includes generated cache and virtual environment folders locally, which are not part of the core application logic.

## 24. Known Issues Already Documented

`CONTEXT.md` mentions:

- CrewAI 0.11.2 has dependency issues on Python 3.14.
- Workarounds were applied and should be documented.
- `langchain-chroma` replaces older Chroma usage through `langchain-community`.
- ChromaDB 1.5.x compatibility was handled in `vector_store.py`.

The Dockerfile uses Python 3.11, which helps avoid the Python 3.14 compatibility issues mentioned in the context file.

## 25. Plain-English Example Flow

Here is what happens when a new machine reading is submitted:

1. A user or device sends machine values to `/ingest/sensor-data`.
2. The API checks that the values are in valid ranges.
3. The API sends the values to the prediction system.
4. The prediction system calculates extra fields such as power, temperature difference, and risk score.
5. The trained Random Forest model estimates failure probability.
6. The system converts that probability into LOW, MEDIUM, HIGH, or CRITICAL.
7. The API saves the original reading.
8. The API saves the prediction.
9. If the risk is HIGH or CRITICAL, the API creates an alert.
10. The user receives a response showing whether an alert was created.

## 26. Final Project Status

The project currently has a working backend foundation for manufacturing predictive maintenance. It can process data, train and use a model, expose predictions through an API, store results, create alerts, search maintenance documents, and prepare AI-agent responses.

The biggest remaining work is productization:

- Improve documentation.
- Build the dashboard.
- Add production authentication.
- Finalize Azure deployment.
- Add alert resolution and maintenance log APIs.
- Replace demo/synthetic data with real plant data when available.
- Clean up encoding issues and placeholder content.

Overall, this is a functional predictive maintenance and manufacturing intelligence backend with ML, API, RAG, agents, testing, and deployment scaffolding already in place.
