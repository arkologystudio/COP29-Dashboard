
# COP29 Narrative Dashboard



---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Getting Started](#getting-started)
3. [Running the Project](#running-the-project)
5. [Additional Notes](#additional-notes)

---

## Prerequisites

Before setting up the project, ensure that you have Git, Python (v3.7 or higher) and Pip are installed.

---

## Getting Started

### 1. Clone the Repository
Begin by cloning the project repository. Open a terminal and run the following command, replacing `<repo-url>` with the actual URL of your Git repository:

```bash
git clone git@github.com:arkologystudio/COP29.git # Provided you are using SSH.
```

### 2. Navigate to the Project Directory
Move into the project folder:

```bash
cd COP29
```

### 3. Install Dependencies
The project’s dependencies are listed in `requirements.txt`.

**Note**: You may consider using a virtual environment to isolate dependencies, especially if working with multiple projects.

To create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate   # For macOS/Linux
env\Scripts\activate      # For Windows
```

After activating the virtual environment, run this to install dependencies:
```bash
pip install -r requirements.txt
```

**Note**: If using VSCode, pressing CTRL + SHIFT + P, selecting "Python: Select Interpreter" > "Create Virtual Environment" and following the prompts can create the venv and install dependencies for you.

---

## Running the Project

After dependencies are installed, launch the Streamlit dashboard using:

```bash
streamlit run dashboard.py
```

This command should open a new browser tab with your Streamlit app. If it doesn’t open automatically, go to [http://localhost:8501](http://localhost:8501) in your browser.

---

## Additional Notes

- **Updating Dependencies**: To add new dependencies, use `pip install <package-name>` and then update `requirements.txt` by running:
  ```bash
  pip freeze > requirements.txt
  ```

