"""Questmind's patch to PDFium, kept thin: one public function.

FPDFImageObj_GetObjectNumber returns the object number of an image object's stream in its
document. The same number is the same image, with the same dictionary, so it decodes the
same way: the corpus PDF catalog decodes a library stamp drawn on every page once per batch
instead of on every page (in Questmind, src/corpus/pdfiumDynamicWorker/worker.js.txt).
Two images with the same bytes and a different /Decode have different numbers. An inline
image has none (0).

Idempotent: applied twice (the workflow's "Patch - Check"), it changes nothing the second
time.
"""

import os

NAME = "FPDFImageObj_GetObjectNumber"

HEADER_ANCHOR = """FPDF_EXPORT unsigned long FPDF_CALLCONV
FPDFImageObj_GetImageDataRaw(FPDF_PAGEOBJECT image_object,
                             void* buffer,
                             unsigned long buflen);
"""

HEADER_ADDITION = """
// Experimental API (Questmind).
// Get the object number of the stream of |image_object| in its document. The same
// number is the same image, decoded the same way.
//
//   image_object - handle to an image object.
//
// Returns the object number, or 0 for an inline image or on failure.
FPDF_EXPORT unsigned long FPDF_CALLCONV
FPDFImageObj_GetObjectNumber(FPDF_PAGEOBJECT image_object);
"""

SOURCE_ADDITION = """
FPDF_EXPORT unsigned long FPDF_CALLCONV
FPDFImageObj_GetObjectNumber(FPDF_PAGEOBJECT image_object) {
  CPDF_ImageObject* pImgObj = CPDFImageObjectFromFPDFPageObject(image_object);
  if (!pImgObj) {
    return 0;
  }

  RetainPtr<CPDF_Image> pImg = pImgObj->GetImage();
  if (!pImg || pImg->IsInline()) {
    return 0;
  }

  RetainPtr<const CPDF_Stream> pImgStream = pImg->GetStream();
  return pImgStream ? pImgStream->GetObjNum() : 0;
}
"""


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def apply(source_dir):
    header = os.path.join(source_dir, "public", "fpdf_edit.h")
    content = _read(header)
    if NAME in content:
        print(f"Skipped: {NAME} declaration")
    else:
        if content.count(HEADER_ANCHOR) != 1:
            raise RuntimeError(f"{header}: the anchor for {NAME} isn't there once")
        _write(header, content.replace(HEADER_ANCHOR, HEADER_ANCHOR + HEADER_ADDITION))
        print(f"Applied: {NAME} declaration")

    source = os.path.join(source_dir, "fpdfsdk", "fpdf_editimg.cpp")
    content = _read(source)
    if NAME in content:
        print(f"Skipped: {NAME} definition")
    else:
        _write(source, content.rstrip("\n") + "\n" + SOURCE_ADDITION)
        print(f"Applied: {NAME} definition")
