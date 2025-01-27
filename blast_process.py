import requests
import time
import sys
from datetime import datetime


def submit_blast_query(sequence, database="nt", program="blastn"):
    """
    Submits a BLAST query to NCBI servers and returns the RID (Request ID).
    """
    url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    params = {
        "CMD": "Put",
        "DATABASE": database,
        "PROGRAM": program,
        "QUERY": sequence,
        "FORMAT_TYPE": "XML",  # Use XML for detailed results parsing
    }
    response = requests.post(url, data=params)
    
    if "RID = " in response.text:
        rid = response.text.split("RID = ")[1].split("\n")[0].strip()
        return rid
    return None


def check_blast_status(rid):
    """
    Checks the status of the BLAST job.
    """
    url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    params = {
        "CMD": "Get",
        "RID": rid,
        "FORMAT_TYPE": "Text",
        "INFO": "STATUS",
    }
    response = requests.get(url, params=params)
    if "Status=READY" in response.text:
        return True
    elif "Status=WAITING" in response.text:
        return False
    return None


def fetch_blast_results(rid):
    """
    Fetches BLAST results for the given RID.
    """
    url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    params = {
        "CMD": "Get",
        "RID": rid,
        "FORMAT_TYPE": "XML",  # Use XML for parsing
    }
    response = requests.get(url, params=params)
    return response.text


def parse_blast_result(xml_result):
    """
    Parses the BLAST XML result to check for matches.
    Returns the best match ID or -1 if no match is found.
    Filters matches based on percent identity > 99% and bit score > 54998.
    """
    if "<BlastOutput_iterations>" not in xml_result:
        return -1  # No match found

    matches = []
    percent_identity = 0.0
    bit_score = 0.0
    align_len = 0

    # Parse for hits with percent identity > 99% and bit score > 54998
    for line in xml_result.splitlines():
        line = line.strip()
        if "<Hsp_identity>" in line:
            identity = int(line.split(">")[1].split("<")[0].strip())
        if "<Hsp_align-len>" in line:
            align_len = int(line.split(">")[1].split("<")[0].strip())
        if "<Hsp_bit-score>" in line:
            bit_score = float(line.split(">")[1].split("<")[0].strip())

            if align_len > 0:
                percent_identity = (identity / align_len) * 100

            if percent_identity > 99 and bit_score > 54998:
                matches.append(1)

    return 1 if matches else -1


def split_sequence(sequence, chunk_size=1000):
    """
    Splits the sequence into chunks of `chunk_size`.
    """
    return [sequence[i:i + chunk_size] for i in range(0, len(sequence), chunk_size)]


def process_sequence(input_file, max_sequence_length=5000):
    """
    Reads a sequence from a file, truncates it to a desired length (e.g., max 5000 characters),
    and processes it into chunks for BLAST comparison.
    """
    try:
        with open(input_file, "r") as file:
            sequence_id = ""
            sequence = ""
            for line in file:
                if line.startswith(">"):
                    sequence_id = line.strip()[1:]  # Get sequence ID without ">"
                else:
                    sequence += line.strip()
    except FileNotFoundError:
        #print(f"Error: File {input_file} not found.")
        exit(1)

    # Truncate the sequence if it's longer than max_sequence_length
    sequence = sequence[:max_sequence_length]

    # Split the sequence into chunks
    return split_sequence(sequence)

def parse_blast_result_detailed(xml_result):
    """
    Parses the BLAST XML result to check for matches.
    Returns detailed information: best match ID, percent identity, and bit score.
    Filters matches based on percent identity > 99% and bit score > 54998.
    """
    if "<BlastOutput_iterations>" not in xml_result:
        return -1, 0.0, 0.0  # No match found

    matches = []
    best_match_id = -1
    percent_identity = 0.0
    bit_score = 0.0
    align_len = None
    identity = 0

    for line in xml_result.splitlines():
        line = line.strip()

        if "<Hsp_identity>" in line:
            identity = int(line.split(">")[1].split("<")[0].strip())
        elif "<Hsp_align-len>" in line:
            align_len = int(line.split(">")[1].split("<")[0].strip())
        elif "<Hsp_bit-score>" in line:
            bit_score = float(line.split(">")[1].split("<")[0].strip())

            # Ensure align_len is not None before calculation
            if align_len and align_len > 0:
                percent_identity = (identity / align_len) * 100

            # Filter matches
            if percent_identity > 99 and bit_score > 54998:
                matches.append(1)

    if matches:
        best_match_id = 1  # Indicating a match was found

    return best_match_id, percent_identity, bit_score



def write_results_to_file(chunks, results, output_file):
   with open(output_file, "w") as file:
    sequence_number = 1  # Initialize the sequence number
    for chunk_id, (chunk, result) in enumerate(zip(chunks, results), start=1):
        best_match_id, percent_identity, bit_score = parse_blast_result_detailed(result)
        chunk_parts = [chunk[i:i + 20] for i in range(0, len(chunk), 20)]
        for part in chunk_parts:
            file.write(f"{sequence_number},{part},{best_match_id}\n")
            sequence_number += 1  # Increment the sequence number





if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: No file path provided. Please pass the file path as an argument.")
        sys.exit(1)

    input_file = sys.argv[1]  # Get the input file path

    # Step 1: Process the input sequence file and divide into chunks
    chunks = process_sequence(input_file)

    # Store the results
    results = []

    for chunk in chunks:
        # Submit BLAST query for each chunk
        rid = submit_blast_query(chunk)
        if not rid:
            print("Error: Failed to submit BLAST query for chunk.")
            continue

        # Poll for results
        while True:
            status = check_blast_status(rid)
            if status is True:
                break
            elif status is False:
                time.sleep(5)  # Reduced delay to improve responsiveness
            else:
                print(f"Error occurred while checking status for chunk.")
                continue

        # Fetch and store results for the chunk
        results.append(fetch_blast_results(rid))

    # Step 6: Save results in the desired format
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"blast_results_{current_datetime}.txt"

    # Write structured results
    write_results_to_file(chunks, results, output_file)

    print(f"{output_file}")