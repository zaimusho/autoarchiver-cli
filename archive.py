#!/usr/bin/python3

import os
import datetime


def get_date_from_parts(year, month, day):
    [iyear, imonth, iday] = map(int, [
        year, month, day
    ])
    return datetime.datetime(iyear, imonth, iday)


def get_date_from_string(string):
    import re

    if string is None:
        return None

    sep = "(_|-|\\.|\\:|\\/)?"
    date_iso = re.compile(
        "^.*" +             # whatever
        "(\\d{4})" + sep +  # year 1
        "(\\d{2})" + sep +  # month 3
        "(\\d{2})" +        # day 5
        ".*$"               # whatever
    )
    m = date_iso.match(string)
    if m is not None:
        [year, i1, month, i2, day] = m.groups()
        return get_date_from_parts(year, month, day)

    date_normal = re.compile(
        "^.*" +             # whatever
        "(\\d{2})" + sep +  # day 1
        "(\\d{2})" + sep +  # month 3
        "(\\d{4})" +        # year 5
        ".*$"               # whatever
    )
    m = date_normal.match(string)
    if m is not None:
        [day, i1, month, i2, year] = m.groups()
        return get_date_from_parts(year, month, day)

    date_no_year = re.compile(
        "^.*" +             # whatever
        "(\\d{2})" + sep +  # day 1
        "(\\d{2})"          # month 3
        ".*$"               # whatever
    )
    m = date_no_year.match(string)
    if m is not None:
        [day, i1, month] = m.groups()
        year = datetime.datetime.now().year
        return get_date_from_parts(year, month, day)

    return None


def open_silently(command, error_message, custom_stdin=None):
    import subprocess

    print("Exec: %r" % command)
    
    stdin_value = None
    if custom_stdin:
        stdin_value = subprocess.PIPE

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=stdin_value
    )

    if stdin_value:
        proc.stdin.write(custom_stdin)
        proc.stdin.flush()
        proc.stdin.close()

    output = proc.stdout.read()
    retcode = proc.wait()
    if retcode is not 0:
        raise Exception((error_message + ":\n%r") % output)


def scan_document():
    import tempfile

    # scan original
    fid, scanned = tempfile.mkstemp(suffix=".tiff")
    open_silently([
        "scanimage", "--resolution=300", "--format=tiff", scanned
    ], "Error attempting to scan document.")
    return scanned


def ocr_document(source):
    import tempfile

    # preprocess for OCR
    fid, tesseract_source = tempfile.mkstemp(suffix=".tiff")
    open_silently([
        "convert", "-quiet", "-density", "150", "-depth", "8",
        "-colorspace", "Gray",
        # avoid alpha channel. required so that processed PDFs can be
        # processed by leptonica and tesseract.
        "-background", "white", "-flatten", "+matte",
        source, tesseract_source
    ], "Error preparing scanned document for tesseract.")

    # OCR scanned document
    fid, tesseract_txt = tempfile.mkstemp(suffix=".txt")
    # automatically created by tesseract!
    tesseract_html = tesseract_txt.replace(".txt", ".html")
    open_silently([
        "tesseract", tesseract_source, tesseract_txt,
        "-l", "nor", "hocr"
    ], "Error processing document with tesseract.")

    # combine source TIFF and ocr data to PDF
    fid, pdf = tempfile.mkstemp(suffix=".pdf")
    with open(tesseract_html, "r") as f:
        html = f.read()
        open_silently([
            "hocr2pdf", "-r", "-150", "-i", tesseract_source,
            "-o", pdf
        ], "Errror processing document!", custom_stdin=html)

    # remove temp-files
    os.unlink(tesseract_source)
    os.unlink(tesseract_html)

    return [pdf, tesseract_txt]


def process(filename, date, tags):
    filename = os.path.expanduser(filename)
    if not os.path.isfile(filename):
        raise Exception(
            "Cannot process file: '{0}'. File not found!".format(filename)
        )

    # print("Processing file '{0}' with date '{1}' and tags {2}".format(
    #     filename, datetime.datetime.strftime(date), tags
    # ))

    # [pdf,txt] = ocr_document(filename)
    res = ocr_document(filename)
    print("%r" % res)


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--date", "-d", help="Date of the archived document.")
    p.add_argument("--file", "-f", help="The file to archive. If omitted, document will be retrieved from scanner.")
    p.add_argument("tags", nargs="*", help="The tags to apply to the document.")

    args = p.parse_args()

    date = get_date_from_string(args.date)
    filename = args.file
    scanned = False

    if filename is None:
        filename = scan_document()
        scanned = True

    process(filename, date, args.tags)

    # delete our temporary copy
    if scanned:
        os.unlink(filename)


if __name__ == "__main__":
    main()
