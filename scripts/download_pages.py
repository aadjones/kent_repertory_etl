import os
import sys

import requests


def download_page(num, page, output_dir="data/raw"):
    """
    Download a single HTML page given the numeric part and page number.

    The URL pattern is:
      http://[base]/kent{num_formatted}.htm#P{page}

    The downloaded file is saved as "kent{num_formatted}_P{page}.html" in the output directory.
    """
    # Decide the base URL based on the numeric value. Kent volumes are split into three parts.
    # The zeroth part is from 0000 to 304, the first part is from 305 to 724, the second part is from 725 to 1074,
    # and the third part is from 1075 to 1420.
    base_url = "http://homeoint.org/books/kentrep/"  # zeroth part
    if num >= 305 and num < 725:
        base_url = "http://homeoint.org/books/kentrep1/"  # first part
    elif num >= 725 and num < 1075:
        base_url = "http://homeoint.org/books/kentrep2/"  # second part
    elif num >= 1075:
        base_url = "http://homeoint.org/books/kentrep3/"  # third part

    num_str = f"{num:04d}"  # zero-padded 4-digit number
    url = f"{base_url}kent{num_str}.htm#P{page}"

    print(f"Downloading {url} ...")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Error downloading {url}: {e}")
        return False  # Indicate failure

    # Ensure the output directory exists.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = f"kent{num_str}_P{page}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(response.text)

    print(f"Saved to {filepath}")
    return True


def download_all_pages(start=0, end=1420, step=5):
    """
    Download all HTML pages from num=start to num=end (inclusive),
    where the numeric part increments by 'step' and the page number
    is always num + 1.
    """
    count = 0

    for num in range(start, end + 1, step):
        page = num + 1  # page number follows the rule: 0000 -> 1, 0005 -> 6, etc.
        success = download_page(num, page)
        count += 1
        if not success:
            print(f"Failed to download page for num={num}, page={page}.")

    print(f"Finished downloading {count} pages.")


def main():
    """
    Main entry point.

    The script accepts an optional command line argument:
      - If "all" is passed as an argument, it downloads all pages.
      - Otherwise, it can download a single page by providing two numbers:
            python download_pages.py <num> <page>
        For example:
            python download_pages.py 0 1
    If no arguments are passed, it defaults to downloading all pages.
    """
    if len(sys.argv) == 3:
        # Download a single page specified by command-line arguments.
        try:
            num = int(sys.argv[1])
            page = int(sys.argv[2])
        except ValueError:
            print("Please provide two integers: <num> and <page>.")
            sys.exit(1)
        download_page(num, page)
    else:
        # If any argument is provided that isn't two numbers, or none provided, download all pages.
        print("No specific page provided. Downloading all pages from num=0000 to 1420.")
        download_all_pages()


if __name__ == "__main__":
    main()
