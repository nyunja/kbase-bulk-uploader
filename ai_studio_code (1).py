import pandas as pd
import requests
import time

def main():
    input_csv = "parsed_data.csv"
    output_csv = "parsed_data_with_ftp_links.csv"

    # 1. Load the data from the previous step
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: '{input_csv}' not found. Please run the PDF extraction script first.")
        return

    ftp_links_1 = []
    ftp_links_2 =[]

    print(f"Searching ENA database for {len(df)} run accessions. This will take a moment...\n")

    # 2. Loop through every row in your CSV
    for index, row in df.iterrows():
        run_acc = row['ena_run_acc']
        
        # ENA's official API URL to request file reports for an accession
        api_url = f"https://www.ebi.ac.uk/ena/portal/api/filereport?accession={run_acc}&result=read_run&fields=fastq_ftp&format=json"
        
        try:
            # Request the data from ENA
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200 and response.json():
                # ENA returns the FTP links combined in one string, separated by a semicolon (;)
                ftp_string = response.json()[0].get('fastq_ftp', '')
                links = ftp_string.split(';')
                
                # Assign the first and second link
                link_1 = links[0] if len(links) > 0 else ""
                link_2 = links[1] if len(links) > 1 else ""
                
                ftp_links_1.append(link_1)
                ftp_links_2.append(link_2)
                
                print(f"[{index+1}/{len(df)}] Success: {run_acc} -> Found {len(links)} link(s)")
            else:
                ftp_links_1.append("")
                ftp_links_2.append("")
                print(f"[{index+1}/{len(df)}] Not Found: {run_acc}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{index+1}/{len(df)}] Network Error on {run_acc}: {e}")
            ftp_links_1.append("")
            ftp_links_2.append("")
            
        # Be polite to the EBI servers (sleep for half a second between requests)
        time.sleep(0.5)

    # 3. Add the extracted links as new columns to our data
    df['ftp_link_1'] = ftp_links_1
    df['ftp_link_2'] = ftp_links_2

    # 4. Save the final results
    df.to_csv(output_csv, index=False)
    print(f"\nDone! File saved as '{output_csv}'")

if __name__ == "__main__":
    main()