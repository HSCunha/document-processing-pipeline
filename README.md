# Python Azure Storage Explorer with React Frontend

This project contains a web-based Azure Storage Explorer with a Python Flask backend, and a separate React frontend.

**Note:** The backend has been updated to an Azure Storage Explorer and is no longer directly integrated with the initial React frontend. The backend serves its own HTML templates. The frontend can be run independently, but it will not communicate with the new backend without further modifications.

## About the Project

### Backend (Azure Storage Explorer)
The backend is a Flask application that allows you to connect to an Azure Storage account and perform the following actions:
*   List containers
*   Browse folders within containers
*   Upload and download blobs
*   Delete blobs
*   Create folders
*   Preview certain file types (JSON, CSV, Parquet)

### Frontend (React App)
The frontend is a basic React application created with `create-react-app`.

## Requirements

### Backend
*   Python 3.x
*   A Python virtual environment (`venv`) is highly recommended.
*   The packages listed in `backend/requirements.txt`.

### Frontend
*   Node.js and npm (or yarn)
*   The packages listed in `frontend/package.json`.

## Getting Azure Credentials

The application's backend requires credentials to connect to your Azure Storage Account. You can use a connection string or an **Account URL** and a **SAS Token**. Here’s how to get the Account URL and SAS Token from the Azure Portal.

### Step 1: Find Your Storage Account URL

1.  Sign in to the [Azure Portal](https://portal.azure.com).
2.  Navigate to your **Storage Account**.
3.  In the left-hand menu, scroll down to the **Settings** section and click on **Endpoints**.
4.  Locate the **Blob service** endpoint.
5.  Copy the URL. This is the value you will use for the `Account URL` field.

    *Example: `https://yourstorageaccount.blob.core.windows.net/`*

### Step 2: Generate a Shared Access Signature (SAS) Token

1.  While in your Storage Account, navigate to the **Security + networking** section in the left-hand menu and click on **Shared access signature**.
2.  Configure the permissions for the token. For this application to have full functionality, use the following settings:
    *   **Allowed services**: Ensure **Blob** is checked.
    *   **Allowed resource types**: Check **Service**, **Container**, and **Object**.
    *   **Allowed permissions**: To enable all features (view, upload, delete), it is recommended to check **Read, Write, Delete, List, Add, and Create**. At a minimum, you need `Read` and `List` to browse and download.
3.  Set an **expiry date** for the token. Be mindful that after this date, the token will no longer work.
4.  Click the **Generate SAS and connection string** button at the bottom of the page.
5.  A new set of fields will appear. Copy the value from the **SAS token** field. It should start with `?sv=...`. This is the value you will use for the `Credential (SAS Token)` field.

## Installation and Setup

1.  **Clone the repository (or download the files).**

2.  **Set up the Backend:**
    
    a. **Create and activate a Python virtual environment:**
        Open a terminal in the project's root directory and run:
        *   **For Windows:**
            ```bash
            python -m venv venv
            .\venv\Scripts\activate
            ```
        *   **For macOS/Linux:**
            ```bash
            python3 -m venv venv
            source venv/bin/activate
            ```
    
    b. **Install backend dependencies:**
        With the virtual environment activated, install the required Python packages:
        ```bash
        pip install -r backend/requirements.txt
        ```

3.  **Set up the Frontend:**

    a. **Navigate to the frontend directory:**
        ```bash
        cd frontend
        ```

    b. **Install frontend dependencies (creates node_modules):**
        This command reads the `package.json` file and installs the required libraries into the `node_modules` directory.
        ```bash
        npm install
        ```

    c. **Build the React application (optional):**
        This command bundles the app into static files for production. The new backend does not serve these files, but you can build them to test the frontend build process.
        ```bash
        npm run build
        ```
    
    d. **Navigate back to the root directory:**
        ```bash
        cd ..
        ```

## Running the Applications

### Running the Backend (Azure Storage Explorer)

1.  **Activate the virtual environment (if not already active):**
    From the root directory, run:
    *   **For Windows:** `.\venv\Scripts\activate`
    *   **For macOS/Linux:** `source venv/bin/activate`

2.  **Start the Flask server:**
    ```bash
    python backend/app.py
    ```

3.  **Access the application:**
    Open your web browser and go to [http://localhost:5000](http://localhost:5000). You will see the Azure Storage Explorer interface.

### Running the Frontend (React Dev Server)
You can run the original React frontend separately using its own development server.

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Start the development server:**
    ```bash
    npm start
    ```
3.  **Access the application:**
    Open your web browser and go to [http://localhost:3000](http://localhost:3000) (or the address provided by the `npm start` command). You will see the basic React app.