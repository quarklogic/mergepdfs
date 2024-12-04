#!/home/carram30/anaconda3/bin/python3

from wsgiref.handlers import CGIHandler
from flask import Flask, render_template, request, Response
import requests
import os
import logging
import PyPDF2
import re


app = Flask(__name__)

## Limit uploads to 20 MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000
max_upload = '20 MB'

logging.basicConfig(filename='log/app.log')

def process_pdfs():
    logging.info('[process_pdfs()]')
    uploaded_files = request.files.getlist('pdfs')
    pdf_file_count = len(uploaded_files)
    
    logging.info(f'[process_pdfs()] {pdf_file_count}')
    
    if pdf_file_count < 2:
        return f"ERROR: You must submit at least two files. Please try again"

    
    pdf_files = []
    merged_pdf_filename = f"tmp/{request.form['pdf_filename']}" if request.form['pdf_filename'] else 'tmp/merged_files.pdf'
    merged_pdf_filename = merged_pdf_filename.replace(' ', '_')
 
    
    ## Append the .pdf extension if not included in the filename
    if not re.search('.pdf$', merged_pdf_filename):
        merged_pdf_filename = ''.join([merged_pdf_filename, '.pdf'])
        
    logging.info(f'[process_pdfs()] {merged_pdf_filename=}') 
    
    ## Save the uploaded PDF files
    bad_pdf_filename = ''
    for file in uploaded_files:
        logging.info(f'[process_pdfs()] Processing uploaded pdf file: {file.filename}')
        
        if not re.search('\.pdf$', file.filename, re.IGNORECASE):
            bad_pdf_filename = f'Found bad extension on {file.filename}'
            logging.info(f'[process_pdfs()] {bad_pdf_filename}')
            
            break
        
        if not re.search('^[\w\s\-\_]+\.pdf$', file.filename, re.IGNORECASE):
            bad_pdf_filename = f'Found bad characters in filename {file.filename}'
            logging.info(f'[process_pdfs()] {bad_pdf_filename}')
            
            break    
            
        local_filename = ''.join(['./tmp/', file.filename])
        local_filename = local_filename.replace(' ', '_')
        local_filename = local_filename.lower()
        
        logging.info(f'[process_pdfs()] {local_filename}')
                
        if file.filename != '':
            tmp_filename = ''.join(['./tmp/', file.filename])
            
            logging.info(f'[process_pdfs()] saving {tmp_filename}')
            file.save(tmp_filename)
            
            logging.info(f'[process_pdfs()] renaming {tmp_filename=} to {local_filename=}')
            os.rename(tmp_filename, local_filename)
            pdf_files.append(local_filename)
            
    
    if bad_pdf_filename:
        return f"ERROR: Bad filename: {bad_pdf_filename}"
    
    ## Merge the PDF files
    logging.info(f'[process_pdfs()] merging {pdf_files=}')
    merger = PyPDF2.PdfMerger()
    for pdf_file in pdf_files:
        merger.append(pdf_file)

    merger.write(merged_pdf_filename)
    merger.close()
    
    ## Delete individual pdf files if merged file exists
    ## and is non-zero length
    if os.path.exists(merged_pdf_filename) and os.path.getsize(merged_pdf_filename) > 0:
        for pdf_file in pdf_files:
            os.remove(pdf_file)
            
                
    #post_message = f"{pdf_file_count} PDF files merged successfully to {merged_pdf_filename}"
    return merged_pdf_filename
 
def stream_pdf(merged_pdf_filename):
    
    with open(merged_pdf_filename, 'rb') as pdf_file:
        while True:
            chunk = pdf_file.read(1024)
            if not chunk:
                break
            
            yield chunk   
  
@app.route('/', methods=['GET','POST'])
def index():
    post_message = ''
    
    if request.method == 'POST':
        logging.info('Processing POST request')
        merged_pdf_filename = process_pdfs()
        
        if re.search('^ERROR', merged_pdf_filename):
            ## Return the error message returned by process_pdfs()
            post_message = merged_pdf_filename
            
        else:
            ## Determine filename from the merged_pdf_filename path
            match = re.search('\/([^/]+)$', merged_pdf_filename)
            merged_filename = match.group(1) if match else 'merged_files.pdf'
            
            response = Response(stream_pdf(merged_pdf_filename), mimetype='application/pdf')
            response.headers["Content-Disposition"] = f"attachment; filename={merged_filename}"
            
            return response
    
               
    return render_template("index.html", 
                           post_message=post_message, 
                           max_upload=max_upload,
                           app_uri=request.environ.get('SCRIPT_NAME'))


CGIHandler().run(app)
