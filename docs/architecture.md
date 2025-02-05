# **Kent Repertory ETL: Architecture and Schema**

## **Overview**

The purpose of this project is to transform the digitized HTML content of the Kent Repertory into a structured, normalized JSON format that serves as the basis for a modern ETL (Extract, Transform, Load) pipeline. In Step 0, our parser reads individual HTML files, extracts and cleans up the content, and outputs a JSON file per source file. This JSON captures the hierarchy and metadata of the repertory including subjects, pages, rubrics, subrubrics, and remedies.

## **JSON Schema**

Each processed JSON file (representing one “chapter”) is structured as follows:

* **title**:  
  The title of the chapter, extracted from the `<title>` tag of the HTML file (e.g., `"KENT0000"`).  
* **page\_info** (optional):  
  A metadata object indicating which pages of the book the HTML file covers (e.g., `{"pages_covered": "p. 1-5"}`).  
* **subject**:  
  The overall subject of the chapter (e.g., `"MIND"`). This is fixed for a given HTML file.  
* **pages**:  
  An array of page groups. Each page group represents a contiguous block of pages within the subject and is structured as follows:  
  * **page**:  
    A page marker (e.g., `"P1"`, `"P2"`, …) which is extracted from subject boundary markers like `"MIND p. 1"`.  
  * **rubrics**:  
    An array of rubric objects that belong to that page. Each rubric object contains:  
    * **title**:  
      The title of the rubric (e.g., `"ABSENT-MINDED"`, `"AMOROUS"`).  
      *Note*: Boundary markers like `"MIND p. 1"` are used only to indicate page splits and are not stored as rubrics.  
    * **description**:  
      Additional textual information associated with the rubric.  
    * **remedies**:  
      An array of remedy objects. Each remedy object has:  
      * **name**:  
        The remedy’s name (e.g., `"Acon."`, `"calc."`).  
      * **grade**:  
        An integer indicating the formatting type:  
        * `1` – Plain text (no special formatting)  
        * `2` – Italic (blue text)  
        * `3` – Bold (red text)  
    * **subrubrics**:  
      An array of rubric objects nested under the parent rubric. This structure can be recursive, reflecting the indentation (hierarchy) in the original HTML.

## **Assumptions**

The parser is built under the following assumptions:

* **Subject and Page Boundaries:**  
  * Each HTML file covers a single subject (e.g., `"MIND"`) that spans multiple contiguous pages.  
  * Page boundaries are indicated by rubric titles such as `"MIND p. 1"`, `"MIND p. 2"`, etc. These markers are used only to group rubrics by page and are not included as actual rubric content.  
  * The overall subject is not treated as a rubric; it is a higher-level classification.  
* **Decorative Content:**  
  * Decorative lines (strings composed solely of hyphens, arrows, or combinations thereof) are filtered out.  
  * Any content inside parentheses is removed as it is not relevant in this step (to be processed later if needed).  
* **HTML Structure:**  
  * The source HTML may use nested `<dir>` tags to indicate hierarchy (subrubrics) or may use `<p>` tags in a flat structure. The parser supports both patterns.  
  * Malformed HTML (e.g., unclosed tags) is handled using BeautifulSoup’s robustness and by wrapping remedy snippets in container tags when necessary.  
* **Remedy Formatting:**  
  * Remedy formatting is determined by HTML markup:  
    * Remedies in **bold red** (indicated by `<font COLOR="#ff0000">`) are assigned a grade of 3\.  
    * Remedies in **italic blue** (indicated by `<font COLOR="#0000ff">`) are assigned a grade of 2\.  
    * Remedies with no formatting are assigned a grade of 1\.  
  * This formatting metadata is stored along with each remedy in the JSON output.  
* **Deduplication:**  
  * Duplicate rubrics (i.e., rubrics with identical titles after normalization) within the same page are merged (descriptions concatenated, remedy lists combined with deduplication).

## **Architecture**

The project is organized into two main code files:

### **1\. scraper\_utils.py**

This file contains all the helper functions and utility routines used by the parser, including:

* **HTML Retrieval:**  
  Functions for fetching HTML content from a URL or loading from a local file.  
* **Text Processing:**  
  Functions such as `is_decorative()`, `remove_parentheses()`, and `normalize_subject_title()` for cleaning and standardizing text.  
* **Parsing Functions:**  
  * `parse_directory()`: Recursively parses nested `<dir>` structures to extract rubrics and subrubrics.  
  * `parse_remedy()` and `parse_remedy_list()`: Parse remedy snippets and list, extracting remedy names and formatting grades.  
* **Grouping and Merging:**  
  Functions such as `merge_duplicate_rubrics()` and `group_by_page()` organize rubrics into page boundaries and merge duplicates.  
* **Output Helpers:**  
  Functions for cleaning filenames and saving the final JSON output.

### **2\. scraper.py**

This is the main script that:

* Accepts a command-line argument to either fetch HTML from a URL or load a local HTML file.  
* Uses functions from **scraper\_utils.py** to parse the HTML into a structured Chapter entity.  
* The Chapter entity includes metadata (title, subject, pages) and the hierarchical structure of rubrics and remedies.  
* Saves the processed JSON file into the `data/processed/` directory.

## **Next Steps**

With Step 0 (HTML parsing and JSON output) robustly implemented and well-tested, the following phases of the project include:

1. **ETL Pipeline & Database Integration:**  
   Design a normalized relational database schema (tables for subjects, pages, rubrics, remedies, etc.) and write an ETL process to load the JSON data into the database.  
2. **Further Data Enrichment:**  
   Refine parsing for additional details (e.g., modifiers, cross‑references) and handle any additional formatting or content that needs special processing.  
3. **Logging, Monitoring, and Performance Optimization:**  
   Expand logging and error handling in production runs to manage processing of all 300 HTML files, ensuring scalability and maintainability.

