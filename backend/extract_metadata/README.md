# Metadata Extraction Module (`extract_metadata`)

## Overview

This module is responsible for extracting metadata from various document types. It provides a flexible pipeline for processing documents, including chunking, cleaning, LLM-based passes, and post-processing, utilizing a plugin architecture for extensibility.

## Requirements

The following Python packages are required to run this module:

-   `Flask`
-   `Flask-Cors`
-   `azure-storage-blob`
-   `pandas`
-   `pyarrow`
-   `Pillow`
-   `PyPDF2`
-   `pymupdf`
-   `langdetect`
-   `pymupdf4llm`
-   `python-pptx`
-   `openpyxl`
-   `xlrd`
-   `extract-msg`
-   `azure-identity`
-   `openai`
-   `markdownify`
-   `pydantic`
-   `python-dotenv`

These can typically be found in the main `backend/requirements.txt` file.

## Configuration

This module relies on several environment variables for configuring Azure OpenAI services and other settings. It is highly recommended to set these variables in a `.env` file in the `backend` directory. The `app.py` script is configured to automatically load these variables at startup if `python-dotenv` is installed.

Create a `.env` file in the `backend` directory with the following structure, replacing the placeholder values with your actual credentials and desired settings:

```dotenv
AZURE_OPENAI_ENDPOINT="https://YOUR_AZURE_OPENAI_RESOURCE_NAME.openai.azure.com/"
AZURE_OPENAI_SLM="YOUR_SLM_DEPLOYMENT_NAME"
AZURE_OPENAI_SLM_API_VERSION="2024-02-01"
AZURE_OPENAI_LLM="YOUR_LLM_DEPLOYMENT_NAME"
AZURE_OPENAI_LLM_API_VERSION="2024-02-01"
FLASK_SECRET_KEY="a_very_secret_and_random_string_of_characters"
SLM_EXTRACTION_ATTEMPTS="3"
ENABLE_LLM="False"
```

**Description of Environment Variables:**

*   `AZURE_OPENAI_ENDPOINT`: The base URL for your Azure OpenAI service.
*   `AZURE_OPENAI_SLM`: The deployment name for your Small Language Model (SLM) on Azure OpenAI.
*   `AZURE_OPENAI_SLM_API_VERSION`: The API version to use for your SLM model (e.g., `2024-02-01`).
*   `AZURE_OPENAI_LLM`: The deployment name for your larger Language Model (LLM) on Azure OpenAI, used for fallback if `ENABLE_LLM` is true.
*   `AZURE_OPENAI_LLM_API_VERSION`: The API version to use for your LLM model (e.g., `2024-02-01`).
*   `FLASK_SECRET_KEY`: A secret key used by Flask for session management. **Ensure this is a strong, randomly generated value in production.**
*   `SLM_EXTRACTION_ATTEMPTS`: (Optional) The number of attempts to try SLM extraction before falling back. Defaults to `3`.
*   `ENABLE_LLM`: (Optional) Set to `"True"` to enable fallback to the larger LLM if SLM extraction fails. Defaults to `"False"`.

## Installation

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate # On Windows
    # source venv/bin/activate # On macOS/Linux
    ```
3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The primary entry point for running the metadata extraction application is `app/run.py`.

To run the application:

1.  Ensure you have followed the installation steps, activated your virtual environment, and **configured the necessary environment variables** as described in the "Configuration" section.
2.  Navigate to the `extract_metadata` directory:
    ```bash
    cd extract_metadata
    ```
3.  Execute the `run.py` script:
    ```bash
    python -m app.run
    ```
    *(Note: Depending on how `run.py` is configured, it might start a local server or process files directly. Refer to `app/run.py` for specific command-line arguments or environment variables if any are needed.)*

## Project Structure

-   `app/`: Contains the main application entry point (`run.py`) and application-specific logic.
-   `core/`: Houses the core logic for the metadata extraction pipeline, including chunking, cleaning, LLM interactions, parsing, and schema definitions.
-   `plugins/`: Implements a plugin architecture to support different document types or extraction strategies.
    -   `generic/`: Generic cleaning, parsing, and reference handling for various document types.

