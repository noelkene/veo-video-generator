# Veo 2 Video Generator

A Streamlit application that generates video variants from images using Google's Veo 2 model.

## Features

- Upload images to generate video variants
- Automatic GCS bucket creation and management
- Secure video download links
- Progress tracking during video generation

## Prerequisites

- Python 3.9+
- Google Cloud Platform account
- Vertex AI API enabled
- Cloud Storage API enabled
- Veo 2 API access

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd veo-video-generator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud authentication:
```bash
gcloud auth application-default login
```

5. Run the application locally:
```bash
streamlit run src/app.py
```

## Usage

1. Open the application in your web browser
2. Upload an image file (PNG, JPG, or JPEG)
3. Click "Generate Videos" to start the process
4. Wait for the video generation to complete
5. Download the generated video using the provided link

## Project Structure

```
.
├── src/
│   └── app.py              # Main Streamlit application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## License

MIT License 