# Importing all the required packages/libraries
import streamlit as st
import os
import tempfile
from PIL import Image
from dotenv import load_dotenv
import fitz  # PyMuPDF for PDF processing
import pandas as pd  # For tabular data representation
import json  # For JSON parsing
import google.generativeai as genai
import io
from io import StringIO

# Load environment variables from .env file
# load_dotenv()
# api_key = os.getenv("GOOGLE_API_KEY")
api_key = st.secrets["GOOGLE_API_KEY"]

def get_po_details(image_parts):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        input_prompt = """
                       You are an expert in reading Purchase Orders.
                       Extract the following details from the Purchase Order document:
                       - Vendor Name
                       - Vendor City
                       - Item Code
                       - Item Name
                       - Number of Items Requested
                       - Unit Price
                       - Total Price
                       
                        If any of the above details are missing, please fill them with Null().
                        Present the information as a clean, 
                        table-like DataFrame output in plain text.
                        Do not include any code or extra lines. 
                        Format the table to resemble a typical DataFrame displayed in Python terminals.
                        Map Vendor Name and Vendor City to all the other details.
                       """
        response = model.generate_content([image_parts[0], input_prompt])
        
        import logging
        logging.info(f"Raw response: {response.text}")

        if not response.text:
            raise ValueError("Empty response from the API.")

        return response.text
    except Exception as e:
        st.error(f"Error with Gemini model: {e}")
        return None
    

# Helper function to process uploaded image for Gemini API
def input_image_setup(uploaded_file):
    try:
        if uploaded_file is not None:
            # Read the image file into bytes
            bytes_data = uploaded_file.getvalue()
            image_parts = [
                {
                    "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                    "data": bytes_data
                }
            ]
            return image_parts
        else:
            st.warning("No file uploaded.")
            return None
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None
    
# Helper function to process uploaded PDF for Gemini API
def process_pdf(uploaded_file):
    try:
        pdf_text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            pdf_document = fitz.open(temp_pdf.name)
            for page_num in range(pdf_document.page_count):
                pdf_text += pdf_document[page_num].get_text("text")
            pdf_document.close()
        return pdf_text
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# Setting the Streamlit app background colour
gradient_css = """
<style>
body {
    background: linear-gradient(135deg, #ff7e5f, #feb47b); 
    color: #5F9EA0; 
    font-family: Arial, sans-serif; 
}
</style>
"""

# Initialize Streamlit app
# st.set_page_config(page_title="CPO Helper", layout="wide")
st.markdown(gradient_css, unsafe_allow_html=True)

st.title("CPO Helper")



# Uploading PO Image or PDF
uploaded_file = st.file_uploader("Upload a Purchase Order (JPG, JPEG, PNG, or PDF)", type=["jpg", "jpeg", "png", "pdf"])
image_data = None
pdf_text = None

if uploaded_file:
    file_type = uploaded_file.type
    if file_type in ["image/jpeg", "image/png", "image/jpg"]:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded PO Image", width=800)  # Display uploaded image
        image_data = input_image_setup(uploaded_file)
    elif file_type == "application/pdf":
        pdf_text = process_pdf(uploaded_file)
        if pdf_text:
            st.subheader("Uploaded PDF Content Preview")
            st.text_area("PDF Content", pdf_text[:1500] + "...", height=400)  # Limiting preview text for display
        # Convert PDF text to image format for Gemini
        image_data = [{"mime_type": "text/plain", "data": pdf_text.encode()}]


# Extracting PO Details
if image_data:
    st.subheader("Extracted Purchase Order Details")
       
       
        # Get extracted details from PO using Gemini
    try:
        response = get_po_details(image_data)
       
        # Validate and parse the response
        if response.strip():  # Ensure response is not empty
            df = pd.read_csv(StringIO(response), delimiter='|')

            # Remove unnamed columns dynamically
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df = df.drop(0)

            # Reset index for cleanliness (optional)
            df = df.reset_index(drop=True)

            # Display the DataFrame in the app
            st.dataframe(df)

            # Save to Excel as a downloadable file
            buffer = io.BytesIO()  # Create an in-memory buffer
            df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)

            # Download button
            st.download_button(
                label="Download as Excel",
                data=buffer,
                file_name="data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("The response is empty. Unable to extract data.")
    
    except Exception as e:
        st.error(f"Failed to process the response. Please try again. Error: {e}")
