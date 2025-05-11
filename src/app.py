import streamlit as st
import time
from google import genai
from google.genai.types import GenerateVideosConfig, Image
from google.cloud import storage
import uuid
from datetime import datetime
import os
from PIL import Image as PILImage
import io

# Constants
BUCKET_NAME = "veo-video-generator-bucket"
GCS_BUCKET_PREFIX = "generated-videos"
PROJECT_ID = "platinum-banner-303105"  # Your GCP project ID
LOCATION = "us-central1"  # Your GCP location

# Initialize Google Cloud clients
storage_client = storage.Client(project=PROJECT_ID)
genai_client = genai.Client(
    project=PROJECT_ID,
    location=LOCATION,
    vertexai=True
)

def initialize_bucket():
    """Initialize the GCS bucket if it doesn't exist."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        if not bucket.exists():
            bucket = storage_client.create_bucket(BUCKET_NAME, location="us-central1")
            st.success(f"Created bucket: {BUCKET_NAME}")
        return bucket
    except Exception as e:
        st.error(f"Error initializing bucket: {str(e)}")
        return None

def upload_image_to_gcs(image_bytes, bucket):
    """Upload an image to GCS and return its URI."""
    try:
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"input_images/{timestamp}_{uuid.uuid4()}.png"
        
        # Upload the file
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/png")
        
        return f"gs://{BUCKET_NAME}/{filename}"
    except Exception as e:
        st.error(f"Error uploading image: {str(e)}")
        return None

def generate_videos_from_image(image_gcs_uri, bucket):
    """Generate videos from an image using Veo 2."""
    try:
        # Generate a unique output prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = f"{GCS_BUCKET_PREFIX}/{timestamp}_{uuid.uuid4()}"
        output_gcs_uri = f"gs://{BUCKET_NAME}/{output_prefix}"
        
        # Configure video generation
        operation = genai_client.models.generate_videos(
            model="veo-2.0-generate-001",
            image=Image(
                gcs_uri=image_gcs_uri,
                mime_type="image/png",
            ),
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
            ),
        )
        
        return handle_video_generation(operation, bucket)
            
    except Exception as e:
        st.error(f"Error generating videos: {str(e)}")
        return None

def generate_videos_from_text(prompt, bucket):
    """Generate videos from text using Veo 2."""
    try:
        # Generate a unique output prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = f"{GCS_BUCKET_PREFIX}/{timestamp}_{uuid.uuid4()}"
        output_gcs_uri = f"gs://{BUCKET_NAME}/{output_prefix}"
        
        # Configure video generation
        operation = genai_client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
            ),
        )
        
        return handle_video_generation(operation, bucket)
            
    except Exception as e:
        st.error(f"Error generating videos: {str(e)}")
        return None

def handle_video_generation(operation, bucket):
    """Handle the video generation process and return the video URI."""
    try:
        # Wait for operation to complete
        with st.spinner("Generating videos... This may take a few minutes."):
            while not operation.done:
                time.sleep(15)
                operation = genai_client.operations.get(operation)
                st.write("Still processing...")
        
        if operation.response:
            return operation.result.generated_videos[0].video.uri
        else:
            st.error("Video generation failed")
            return None
            
    except Exception as e:
        st.error(f"Error during video generation: {str(e)}")
        return None

def create_download_link(video_uri, bucket):
    """Create a signed download link for the video."""
    try:
        video_blob = bucket.blob(video_uri.replace(f"gs://{BUCKET_NAME}/", ""))
        video_url = video_blob.generate_signed_url(
            version="v4",
            expiration=3600,  # 1 hour
            method="GET"
        )
        st.markdown(f"[Download Video]({video_url})")
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")

def main():
    st.title("🎥 Veo 2 Video Generator")
    st.write("Generate videos using Google's Veo 2 model from either text or an image.")
    
    # Initialize bucket
    bucket = initialize_bucket()
    if not bucket:
        st.error("Failed to initialize storage bucket")
        return
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["Generate from Image", "Generate from Text"])
    
    with tab1:
        st.header("Generate from Image")
        uploaded_file = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"])
        
        if uploaded_file is not None:
            # Read the file bytes
            image_bytes = uploaded_file.read()
            
            # Display the uploaded image
            image = PILImage.open(io.BytesIO(image_bytes))
            st.image(image, caption="Uploaded Image", use_container_width=True)
            
            if st.button("Generate Videos from Image"):
                # Upload image to GCS
                image_gcs_uri = upload_image_to_gcs(image_bytes, bucket)
                if not image_gcs_uri:
                    st.error("Failed to upload image")
                    return
                
                # Generate videos
                video_uri = generate_videos_from_image(image_gcs_uri, bucket)
                if video_uri:
                    st.success("Video generation completed!")
                    st.write(f"Video URI: {video_uri}")
                    create_download_link(video_uri, bucket)
    
    with tab2:
        st.header("Generate from Text")
        prompt = st.text_area("Enter your prompt", 
                            placeholder="Describe the video you want to generate...",
                            height=150)
        
        if prompt and st.button("Generate Videos from Text"):
            # Generate videos
            video_uri = generate_videos_from_text(prompt, bucket)
            if video_uri:
                st.success("Video generation completed!")
                st.write(f"Video URI: {video_uri}")
                create_download_link(video_uri, bucket)

if __name__ == "__main__":
    main() 