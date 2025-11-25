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

The primary entry point for running the metadata extraction application is `app/run.py`. This script is designed to be run from the command line, accepting a file path and an optional pipeline type.

### Running the Extraction

1.  **Ensure you are in the correct directory.** All commands should be run from the `backend/extract_metadata` directory.
    ```bash
    cd path/to/your/project/backend/extract_metadata
    ```
2.  **Make sure your virtual environment is activated** and you have configured the necessary environment variables as described in the "Configuration" section.
3.  **Execute the `run.py` script** using `python -m app.run`, providing the path to the file you want to process.

### Command-Line Arguments

-   `--file`: (Required) The full or relative path to the document you want to process.
-   `--pipeline`: (Optional) The type of pipeline to use. Can be `sop` or `generic`. Defaults to `sop`.

### Example: Extracting Metadata from a PDF

To extract metadata from a `filename.pdf` file located in `data/raw/` using the SOP pipeline, you would run the following command from within the `backend/extract_metadata` directory:

```bash
python -m app.run --file data/raw/filename.pdf --pipeline sop
```

The script will process the file and print the extracted metadata to the console in JSON format.


## Project Structure

-   `app/`: Contains the main application entry point (`run.py`) and application-specific logic.
-   `core/`: Houses the core logic for the metadata extraction pipeline, including chunking, cleaning, LLM interactions, parsing, and schema definitions.
-   `plugins/`: Implements a plugin architecture to support different document types or extraction strategies.
    -   `generic/`: Generic cleaning, parsing, and reference handling for various document types.

## Creating a Custom Pipeline

The metadata extraction module is designed to be extensible through a plugin architecture. You can create your own custom pipeline to handle new document types or implement a different extraction workflow. Here are the steps to create a new pipeline called `my_pipeline`.

### 1. Create the Pipeline Directory

First, create a new directory for your pipeline under `backend/extract_metadata/plugins/`:

```bash
mkdir backend/extract_metadata/plugins/my_pipeline
```

### 2. Create the Pipeline Modules

Inside the `backend/extract_metadata/plugins/my_pipeline` directory, create the following Python files. These files will contain the logic for the different components of your pipeline.

*   `__init__.py` (an empty file to make the directory a Python package)
*   `cleaning.py`: For data cleaning and preprocessing.
*   `filename_parser.py`: To extract information from filenames.
*   `passes.py`: To define the LLM extraction passes and schemas.
*   `references.py`: To define how to extract and handle references.
*   `schema_map.py`: To map the extracted data to your final output schema.

### 3. Implement Your Custom Logic

Flesh out the logic in each of the files you created. You should follow the structure of the existing `generic` pipeline as a reference.

**`cleaning.py`:**
Define a function that returns a `CleaningPipeline`.

```python
# backend/extract_metadata/plugins/my_pipeline/cleaning.py
from extract_metadata.core.cleaning import CleaningPipeline, CleaningStep

def get_my_pipeline_cleaning_pipeline() -> CleaningPipeline:
    """Returns the cleaning pipeline for my_pipeline."""
    steps = [
        # Add your CleaningStep instances here
    ]
    return CleaningPipeline(steps=steps)
```

**`filename_parser.py`:**
Create a custom filename parser class.

```python
# backend/extract_metadata/plugins/my_pipeline/filename_parser.py
from extract_metadata.core.pipeline import BaseFilenameParser

class MyPipelineFilenameParser(BaseFilenameParser):
    def parse(self, filename: str) -> dict:
        # Implement your filename parsing logic here
        return {"document_type": "my_document_type"}
```

**`passes.py`:**
Define the Pydantic schema for your metadata and the LLM pass.

```python
# backend/extract_metadata/plugins/my_pipeline/passes.py
from pydantic import BaseModel
from extract_metadata.core.llm_passes import BaseLLMPass, LLMPassPipeline
from extract_metadata.core.parsing import JsonOutputParser

class MyPipelineMetadataSchema(BaseModel):
    # Define your metadata fields here
    title: str
    author: str

def get_my_pipeline_llm_pipeline() -> LLMPassPipeline:
    """Factory function to create a my_pipeline LLM pipeline."""
    
    class MyPipelineLLMPass(BaseLLMPass):
        def __init__(self, **kwargs):
            super().__init__(
                name="MyPipelineLLMPass",
                output_schema=MyPipelineMetadataSchema,
                **kwargs
            )

        def get_system_prompt(self) -> str:
            return "Your custom system prompt here."

    llm_pass = MyPipelineLLMPass(json_cleaner=JsonOutputParser())
    return LLMPassPipeline(passes=[llm_pass])
```

**`references.py`:**
Define and register a reference extractor.

```python
# backend/extract_metadata/plugins/my_pipeline/references.py
from extract_metadata.core.references import RegexReferenceExtractor, ReferenceExtractorRegistry

class MyPipelineReferenceExtractor(RegexReferenceExtractor):
    def __init__(self):
        patterns = [r"REGEX_TO_FIND_REFERENCES"]
        super().__init__(patterns=patterns, standardize_func=lambda x: x.lower())

ReferenceExtractorRegistry.register_extractor("my_pipeline_refs", MyPipelineReferenceExtractor)
```

**`schema_map.py`:**
Define the schema mapper.

```python
# backend/extract_metadata/plugins/my_pipeline/schema_map.py
from extract_metadata.core.schema import SchemaMapper

MY_PIPELINE_OUTPUT_SCHEMA_MAP = {
    "title": "/document/title",
    "author": "/document/author",
}

my_pipeline_schema_mapper = SchemaMapper(MY_PIPELINE_OUTPUT_SCHEMA_MAP)
```

### 4. Integrate the New Pipeline into `run.py`

Finally, you need to make the application aware of your new pipeline.

1.  **Open `backend/extract_metadata/app/run.py`.**

2.  **Import your new pipeline's components** at the top of the file:

    ```python
    # My Pipeline components
    from extract_metadata.plugins.my_pipeline.filename_parser import MyPipelineFilenameParser
    from extract_metadata.plugins.my_pipeline.cleaning import get_my_pipeline_cleaning_pipeline
    from extract_metadata.plugins.my_pipeline.references import MyPipelineReferenceExtractor
    from extract_metadata.plugins.my_pipeline.passes import get_my_pipeline_llm_pipeline
    from extract_metadata.plugins.my_pipeline.schema_map import my_pipeline_schema_mapper
    ```

3.  **Create a setup function** for your pipeline in `run.py`. This function will instantiate and configure your pipeline's components.

    ```python
    def setup_my_pipeline_pipeline() -> MetadataPipeline:
        """Sets up the 'my_pipeline' metadata extraction pipeline."""
        logger.info("Setting up My Pipeline metadata extraction pipeline.")
        
        filename_parser = MyPipelineFilenameParser()
        cleaning_pipeline = get_my_pipeline_cleaning_pipeline()
        llm_pass_pipeline = get_my_pipeline_llm_pipeline()
        post_processor = MetadataPostProcessor(reference_extractor_name="my_pipeline_refs")

        return MetadataPipeline(
            filename_parser=filename_parser,
            chunker=PyMuPDFChunker(), # Or your preferred chunker
            cleaning_pipeline=cleaning_pipeline,
            llm_pass_pipeline=llm_pass_pipeline,
            post_processor=post_processor,
            schema_mapper=my_pipeline_schema_mapper,
            # Add other components as needed
        )
    ```

4.  **Add your pipeline to the command-line arguments.** Find the `parser.add_argument` call for the `--pipeline` argument and add `'my_pipeline'` to the `choices` list.

    ```python
    parser.add_argument("--pipeline", type=str, default="sop", choices=["sop", "generic", "my_pipeline"], help="The pipeline to use.")
    ```

5.  **Add the logic to select your pipeline** in the `main` function.

    ```python
    if __name__ == "__main__":
        # ... (argument parsing logic) ...

        if args.pipeline == "sop":
            pipeline = setup_sop_pipeline()
        elif args.pipeline == "generic":
            pipeline = setup_generic_pipeline()
        elif args.pipeline == "my_pipeline":
            pipeline = setup_my_pipeline_pipeline()
        else:
            raise ValueError(f"Unknown pipeline type: {args.pipeline}")
        
        # ... (rest of the main function) ...
    ```

After completing these steps, you can run your new pipeline from the command line:

```bash
python -m app.run --file path/to/your/file.pdf --pipeline my_pipeline
```
