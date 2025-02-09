import sys
import argparse
import io
import matchmaker.ibkr as ibkr
import pandas as pd

prefixes_to_keep = [
    "Statement",
    "Account Information,Header,Field Name",
    "Account Information,Data,Account",
    "Trades",
    "Corporate Actions",
    "Mark-to-Market Performance Summary",
    "Transfers"
]
tables_to_keep = ['Account Information'] + prefixes_to_keep

columns_to_multiply = [
    "Quantity",
    "Prior Quantity",
    "Current Quantity",
    "Prior Price",
    "Current Price",
    "Mark-to-Market P/L Position",
    "Mark-to-Market P/L Transaction",
    "Mark-to-Market P/L Commissions",
    "Mark-to-Market P/L Other",
    "Mark-to-Market P/L Total",
    "Proceeds",
    "Comm/Fee",
    "Basis",
    "Realized P/L",
    "MTM P/L",
    "Qty",
    "Xfer Price",
    "Market Value",
    "Realized P/L",
    "Cash Amount"
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anonymize IBKR report by removing personal information, net worth and anything that's not directly needed to match trades." 
                                     "Example usage: anonymize.py report_2024.csv --remove AAPL,TSLA,BABA")
    parser.add_argument("input", help="Input IBKR report")
    parser.add_argument("--output", "-o", help="Output report file. If not specified, the input file will be used with _anonymized appended.")
    parser.add_argument("--remove", "-r", action="append", help="Comma-separated tickers to remove from the report. Use this to narrow it down to only what you want to share.", default=[])
    parser.add_argument("--multiplier", "-m", help="Multiplies all transactions by this number, hiding your real volume. Use this to truly anonymize your report, especially if you'd like to share it with the devs or other parties without disclosing your net worth.", type=float, default=1.0)

    try:
        args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)

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

    output = ""
    with open(input_file, 'r') as infile:
        for line in infile:
            if any(line.startswith(prefix + ',') for prefix in prefixes_to_keep) and not should_remove_line(line, symbols_to_remove):
                output += line

    if args.multiplier != 1.0:
        output_wrapper = io.BytesIO(output.encode('utf-8')) 
        output = ""
        lines = ibkr.parse_csv_into_prefixed_lines(output_wrapper)
        with open(output_file, 'w') as outfile:
            for prefix in tables_to_keep:
                df = ibkr.dataframe_from_prefixed_lines(lines, prefix)
                if df is not None:
                    for column in columns_to_multiply:
                        if column in df.columns:
                            df[column] = pd.to_numeric(df[column].replace(',', '', regex=True), errors='coerce')
                            df[column] = df[column] * args.multiplier
                    output += df.to_csv(index=False)

    with open(output_file, 'w', newline='\n') as outfile:
        outfile.write(output)
    print(f"Anonymized report saved to {output_file}")
