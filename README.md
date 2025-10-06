# hackatonCarolina

Repositorio con el Challenge del Hackaton

## Overview

This repository contains the backend developed fot our team @Jupyter engineers to the Hackathon NASA Challenge, "From EarthData to Action: Cloud Computing with Earth Observation Data for Predicting Cleaner, Safer Skies" . The project is primarily developed in Python and includes a `Procfile` for deployment configuration. Below you'll find a step-by-step guide to understand, set up, and run the project.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Features

- Python-based solution to the Hackathon challenge.
- Ready for deployment (Procfile included).
- Easy setup and instructions.

## Requirements

Before you begin, make sure you have the following installed:

- Python 3.7+ ([Download Python](https://www.python.org/downloads/))
- [pip](https://pip.pypa.io/en/stable/)
- (Optional) [Git](https://git-scm.com/)

## Setup

Follow these steps to set up the project:

1. **Clone the Repository**

   ```bash
   git clone https://github.com/testudoDaemon/hackatonCarolina.git
   cd hackatonCarolina
   ```

2. **Create a Virtual Environment (Recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > If `requirements.txt` is not available, manually install required packages as described in the project files.

## Usage

1. **Run the Application**

   The main entry point is typically a Python script (e.g., `app.py`, `main.py`). To start the application, run:

   ```bash
   python app.py
   ```
   or
   ```bash
   python main.py
   ```

   > Check the repository files for the actual entry point.

2. **Access the Application**

   If the project starts a web server, it will display a localhost URL (e.g., `http://127.0.0.1:5000/`). Open this URL in your web browser.

## Deployment

The included `Procfile` allows easy deployment to platforms like Heroku.

1. **Create a Heroku Account**  
   Sign up at [Heroku](https://www.heroku.com/).

2. **Install Heroku CLI**  
   [Heroku CLI Installation Guide](https://devcenter.heroku.com/articles/heroku-cli)

3. **Login to Heroku**

   ```bash
   heroku login
   ```

4. **Create a New Heroku App**

   ```bash
   heroku create your-app-name
   ```

5. **Deploy the App**

   ```bash
   git push heroku main
   ```

   Heroku will use the `Procfile` to start the application.

## Contributing

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is Open Source.
