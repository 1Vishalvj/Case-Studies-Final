import re
import logging
import json
import azure.functions as func

# Create the Function App instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def clean_email_body(email_body):
    # Remove disclaimers first (including those with URLs)
    email_body = re.sub(r'This email may contain confidential information.*?Thank you\.', '', email_body, flags=re.IGNORECASE | re.DOTALL)
    email_body = re.sub(r'This e-mail message may contain confidential and/or privileged information.*?Thank you\.', '', email_body, flags=re.IGNORECASE | re.DOTALL)
    email_body = re.sub(r'CAUTION: This email originated from outside of the organization.*?safe\.', '', email_body, flags=re.IGNORECASE | re.DOTALL)
    
    # Fixed BCG disclaimer regex - made spacing optional and ending more flexible
    email_body = re.sub(r'This e-mail message may contain confidential and/or privileged information\. If you are not an addressee or otherwise authorized to receive this message, you should not use, copy, disclose or take any action based on this e-mail or any information contained in the message\. If you have received this material in error, please advise the sender immediately by reply e-mail and delete this message\.\s*We may share your contact details with other BCG entities and our third party service providers\. Please see BCG privacy policy https://www\.bcg\.com/about/privacy-policy\.aspx for further information\.?', '', email_body, flags=re.IGNORECASE | re.DOTALL)
    
    # Fixed Penguin International disclaimer regex - made spacing optional and ending more flexible
    email_body = re.sub(r'This email may contain confidential Penguin International information\. If received in error or if you\'re not the intended recipient, please notify the sender and delete it\.\s*By accessing this email, you consent to sharing your contact details within our network\. Refer to our privacy policy at https://www\.penguin-international\.com/privacy-policy/ for more details\.?\s*(?:Thank you\.?)?', '', email_body, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove email addresses
    email_body = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', email_body)
    # Remove phone numbers (simple pattern for international, local, and formatted phone numbers)
    email_body = re.sub(r'\+?[0-9]{1,4}?[-.\s]?[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}', '[PHONE]', email_body)
    # Now remove URLs (http, https, and www formats)
    email_body = re.sub(r'http[s]?://\S+|www\.\S+', '[URL]', email_body)
    # Remove 'From', 'To', 'CC' and other email thread metadata
    email_body = re.sub(r'(From|To|CC|Sent|Date):[^\n]*', '', email_body, flags=re.IGNORECASE)
    # Remove replies and email thread indicators (--- or similar marks between replies)
    email_body = re.sub(r'---\s*', '', email_body)
    # Remove specific words or phrases
    email_body = re.sub(r'(Confidential|Proprietary|Private|Sensitive)', '', email_body, flags=re.IGNORECASE)
    # Remove specific company names
    email_body = re.sub(r'(Penguin International|BCG|Boston Consulting Group)', '', email_body, flags=re.IGNORECASE)
    # Remove job titles
    email_body = re.sub(r'(Assistant Manager|Business Analyst|Senior Analyst|Head of Operations)', '', email_body, flags=re.IGNORECASE)
    # Remove meeting details (fixed regex)
    email_body = re.sub(r'Meeting ID: [\w\d]+', '', email_body)
    # Remove date/time references
    email_body = re.sub(r'\b(\d{1,2}[-/th|st|nd|rd]?\s?[A-Za-z]+\s\d{4})\b', '', email_body)
    # Remove inline images or attachments
    email_body = re.sub(r'!\[.*?\]\(.*?\)', '', email_body)
    # Remove HTML tags
    email_body = re.sub(r'<.*?>', '', email_body)
    # Replace newlines and multiple spaces with a single space
    email_body = re.sub(r'\s+', ' ', email_body).strip()
    # If email body is empty after cleaning
    if not email_body:
        email_body = "No meaningful content found in the email."
    return email_body

@app.route(route="clean-email", methods=["POST"])
def clean_email_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    email_body = ""
    
    # Try to get JSON first
    try:
        req_body = req.get_json()
        if req_body:
            # Support multiple field names for flexibility
            email_body = req_body.get('emailBody', '') or req_body.get('email_body', '') or req_body.get('body', '')
        
        # If no valid JSON body found, try plain text
        if not email_body:
            email_body = req.get_body().decode('utf-8')
            
    except (ValueError, UnicodeDecodeError) as e:
        logging.error(f"Error parsing request: {e}")
        # If JSON parsing fails, try plain text
        try:
            email_body = req.get_body().decode('utf-8')
        except UnicodeDecodeError:
            return func.HttpResponse(
                "Error: Could not decode request body.",
                status_code=400,
                mimetype="text/plain"
            )
    
    if not email_body or email_body.strip() == "":
        return func.HttpResponse(
            "Error: No email body provided.",
            status_code=400,
            mimetype="text/plain"
        )

    try:
        # Clean the email body
        cleaned_body = clean_email_body(email_body)
        
        # Return just the cleaned text (simple option)
        return func.HttpResponse(
            cleaned_body,
            status_code=200,
            mimetype="text/plain"
        )
        
        # OR return with statistics (detailed option)
        # response_text = f"""CLEANED EMAIL:
        # {cleaned_body}
        # 
        # STATISTICS:
        # Original Length: {len(email_body)} characters
        # Cleaned Length: {len(cleaned_body)} characters
        # Reduction: {len(email_body) - len(cleaned_body)} characters removed
        # """
        # 
        # return func.HttpResponse(
        #     response_text,
        #     status_code=200,
        #     mimetype="text/plain"
        # )
        
    except Exception as e:
        logging.error(f"Error cleaning email: {e}")
        return func.HttpResponse(
            f"Error processing email: {str(e)}",
            status_code=500,
            mimetype="text/plain"
        )