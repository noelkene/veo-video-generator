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

# Initialize Google Cloud clients using default credentials
try:
    storage_client = storage.Client(project=PROJECT_ID)
    genai_client = genai.Client(
        project=PROJECT_ID,
        location=LOCATION,
        vertexai=True
    )
except Exception as e:
    st.error(f"Error initializing Google Cloud clients: {str(e)}")
    st.error("Please ensure your Cloud Run service has the correct permissions.")
    st.stop()

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

def generate_videos_from_image(image_gcs_uri, bucket, num_videos, duration_seconds):
    """Generate videos from an image using Veo 2."""
    uris = []
    for _ in range(num_videos):
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
                    duration_seconds=duration_seconds,
                ),
            )
            
            result_uris = handle_video_generation(operation, bucket)
            if result_uris:
                uris.extend(result_uris)
        except Exception as e:
            st.error(f"Error generating videos: {str(e)}")
    return uris if uris else None

def generate_videos_from_text(prompt, bucket, num_videos, duration_seconds):
    """Generate videos from text using Veo 2."""
    uris = []
    for _ in range(num_videos):
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
                    duration_seconds=duration_seconds,
                ),
            )
            
            result_uris = handle_video_generation(operation, bucket)
            if result_uris:
                uris.extend(result_uris)
        except Exception as e:
            st.error(f"Error generating videos: {str(e)}")
    return uris if uris else None

def handle_video_generation(operation, bucket):
    """Handle the video generation process and return the video URIs."""
    try:
        # Wait for operation to complete
        with st.spinner("Generating videos... This may take a few minutes."):
            while not operation.done:
                time.sleep(15)
                operation = genai_client.operations.get(operation)
                st.write("Still processing...")
        if operation.response:
            return [v.video.uri for v in operation.result.generated_videos]
        else:
            st.error("Video generation failed")
            return None
            
    except Exception as e:
        st.error(f"Error during video generation: {str(e)}")
        return None

def create_download_links(video_uris, bucket):
    """Create signed download links for the videos."""
    try:
        for idx, video_uri in enumerate(video_uris):
            video_blob = bucket.blob(video_uri.replace(f"gs://{BUCKET_NAME}/", ""))
            url = video_blob.generate_signed_url(
                version="v4",
                expiration=3600,
                method="GET"
            )
            st.markdown(f"**Video {idx+1}:** [Download Video]({url})")
    except Exception as e:
        st.error(f"Error creating download links: {str(e)}")
        st.error("Please ensure your Cloud Run service account has the necessary permissions.")

def main():
    st.title("🎥 Veo 2 Video Generator")
    st.write("Generate videos using Google's Veo 2 model from either text or an image.")
    
    # Initialize bucket
    bucket = initialize_bucket()
    if not bucket:
        st.error("Failed to initialize storage bucket")
        return
    
    # User options
    st.sidebar.header("Video Generation Options")
    num_videos = st.sidebar.selectbox("Number of videos to generate", [1, 2, 3, 4], index=0)
    duration_seconds = st.sidebar.selectbox("Video duration (seconds)", [5, 6, 7, 8], index=0)
    
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
                video_uris = generate_videos_from_image(image_gcs_uri, bucket, num_videos, duration_seconds)
                if video_uris:
                    st.success("Video generation completed!")
                    for uri in video_uris:
                        st.write(f"Video URI: {uri}")
                    create_download_links(video_uris, bucket)
    
    with tab2:
        st.header("Generate from Text")
        prompt = st.text_area("Enter your prompt", 
                            placeholder="Describe the video you want to generate...",
                            height=150)
        
        if prompt and st.button("Generate Videos from Text"):
            # Generate videos
            video_uris = generate_videos_from_text(prompt, bucket, num_videos, duration_seconds)
            if video_uris:
                st.success("Video generation completed!")
                for uri in video_uris:
                    st.write(f"Video URI: {uri}")
                create_download_links(video_uris, bucket)

if __name__ == "__main__":
    main() 