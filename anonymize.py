import sys
import argparse

prefixes = [
    "Statement,",
    "Account Information,Data,Account,",
    "Trades,",
    "Corporate Actions,",
    "Mark-to-Market Performance Summary,",
    "Transfers,"
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anonymize IBKR report by removing personal information, net worth and anything that's not directly needed to match trades.")
    parser.add_argument("input", help="Input IBKR report")
    parser.add_argument("--output", "-o", help="Output report file. If not specified, the input file will be used with _anonymized appended.")
    parser.add_argument("--remove", "-r", action="append", help="Tickers to remove from the report. Use this to narrow it down to only what you want to share.", default=[])
    
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output if args.output else input_file.rsplit('.', 1)[0] + "_anonymized." + input_file.rsplit('.', 1)[1]
    symbols_to_remove = args.remove
    # Some elements may denote multiple comma-separated symbols as a single string, let's merge them into a single list
    symbols_to_remove = [item for sublist in [symbol.split(',') for symbol in symbols_to_remove] for item in sublist]

    def should_remove_line(line, symbols):
        for symbol in symbols:
            if f",{symbol}," in line or f",{symbol}(" in line:
                return True
        return False

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if any(line.startswith(prefix) for prefix in prefixes) and not should_remove_line(line, symbols_to_remove):
                outfile.write(line)
