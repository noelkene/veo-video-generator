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

# Initialize Google Cloud clients
storage_client = storage.Client()
genai_client = genai.Client()

# Constants
BUCKET_NAME = "veo-video-generator-bucket"
GCS_BUCKET_PREFIX = "generated-videos"

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

def upload_image_to_gcs(image_file, bucket):
    """Upload an image to GCS and return its URI."""
    try:
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"input_images/{timestamp}_{uuid.uuid4()}.png"
        
        # Upload the file
        blob = bucket.blob(filename)
        blob.upload_from_file(image_file)
        
        return f"gs://{BUCKET_NAME}/{filename}"
    except Exception as e:
        st.error(f"Error uploading image: {str(e)}")
        return None

def generate_videos(image_gcs_uri, bucket):
    """Generate videos using Veo 2."""
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
        st.error(f"Error generating videos: {str(e)}")
        return None

def main():
    st.title("🎥 Veo 2 Video Generator")
    st.write("Upload an image to generate 4 video variants using Google's Veo 2 model.")
    
    # Initialize bucket
    bucket = initialize_bucket()
    if not bucket:
        st.error("Failed to initialize storage bucket")
        return
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        # Display the uploaded image
        image = PILImage.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Generate Videos"):
            # Upload image to GCS
            image_gcs_uri = upload_image_to_gcs(uploaded_file, bucket)
            if not image_gcs_uri:
                st.error("Failed to upload image")
                return
            
            # Generate videos
            video_uri = generate_videos(image_gcs_uri, bucket)
            if video_uri:
                st.success("Video generation completed!")
                st.write(f"Video URI: {video_uri}")
                
                # Create a download link
                video_blob = bucket.blob(video_uri.replace(f"gs://{BUCKET_NAME}/", ""))
                video_url = video_blob.generate_signed_url(
                    version="v4",
                    expiration=3600,  # 1 hour
                    method="GET"
                )
                st.markdown(f"[Download Video]({video_url})")

if __name__ == "__main__":
    main() 