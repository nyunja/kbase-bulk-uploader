import pdfplumber
import pandas as pd

def extract_metadata_from_pdf(pdf_path, output_csv):
    # The exact columns we want to extract
    target_columns =[
        "country", 
        "city", 
        "ena_sample_acc", 
        "ena_experiment_acc", 
        "ena_run_acc"
    ]
    
    extracted_rows =[]

    print(f"Opening {pdf_path}...")
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract the table structure from the page
            table = page.extract_table()
            
            # Skip if no table is found or it's just a single row
            if not table or len(table) < 2:
                continue
            
            # Standardize headers (make them lowercase, remove extra spaces/newlines)
            headers =[]
            for h in table[0]:
                if h:
                    headers.append(str(h).strip().replace('\n', '').lower())
                else:
                    headers.append("")
            
            # Check if all our target columns exist in this table's header
            if all(col in headers for col in target_columns):
                # Map column names to their index numbers
                col_indices = {col: headers.index(col) for col in target_columns}
                
                # Loop through the data rows (skipping the header row)
                for row in table[1:]:
                    if not any(row):  # Skip completely empty rows
                        continue
                        
                    try:
                        # Extract the data based on the indices we found
                        row_data = {}
                        for col in target_columns:
                            cell_val = row[col_indices[col]]
                            # Clean the text: remove newlines caused by text wrapping in cells
                            clean_val = str(cell_val).replace('\n', ' ').strip() if cell_val else ""
                            row_data[col] = clean_val
                            
                        # Only add rows that actually contain the ENA IDs
                        if str(row_data['ena_sample_acc']).startswith('ERS'):
                            extracted_rows.append(row_data)
                            
                    except IndexError:
                        # Safely skip malformed rows where columns get cut off
                        continue

    # Save everything to a CSV
    if extracted_rows:
        df = pd.DataFrame(extracted_rows)
        df.to_csv(output_csv, index=False)
        print(f"Extraction complete! Saved {len(df)} records to '{output_csv}'.")
    else:
        print("Could not find the target columns or data in the PDF tables. "
              "The table might lack visible border lines.")

if __name__ == "__main__":
    # ---> UPDATE THESE FILE PATHS <---
    INPUT_PDF = "your_file.pdf"   
    OUTPUT_CSV = "parsed_data.csv"
    
    extract_metadata_from_pdf(INPUT_PDF, OUTPUT_CSV)