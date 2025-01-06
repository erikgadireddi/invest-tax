import sys

def anonymize_ibkr_report(input_file, output_file):
    prefixes = [
        "Statement,",
        "Account Information,Data,Account,",
        "Trades,",
        "Corporate Actions,",
        "Mark-to-Market Performance Summary,",
        "Transfers,"
    ]

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if any(line.startswith(prefix) for prefix in prefixes):
                outfile.write(line)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python anonymize.py <input_csv> [<output_csv>]")
        sys.exit(1)

    input_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = input_file.rsplit('.', 1)[0] + "_anonymized." + input_file.rsplit('.', 1)[1]

    anonymize_ibkr_report(input_file, output_file)
