import os
from pathlib import Path
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

def test_chemistry():
    pdf_path = Path("input/chemistry.pdf")
    out_dir = Path("output/chemistry_sample")
    img_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    
    print("Reading PDF...")
    pdf_bytes = pdf_path.read_bytes()
    image_writer = FileBasedDataWriter(str(img_dir))
    md_writer = FileBasedDataWriter(str(out_dir))
    ds = PymuDocDataset(pdf_bytes)
    
    print("Running Doc Analyze on Page 0...")
    infer_result = ds.apply(
        doc_analyze,
        ocr=False,
        start_page_id=0,
        end_page_id=0
    )
    print("Piping to TXT mode...")
    pipe_result = infer_result.pipe_txt_mode(image_writer)
    
    print("Dumping output...")
    pipe_result.dump_md(md_writer, "chemistry_sample.md", "images")
    pipe_result.dump_content_list(md_writer, "chemistry_sample_content_list.json", "images")
    pipe_result.dump_middle_json(md_writer, "chemistry_sample_middle.json")
    
    print("Done! Check output/chemistry_sample")

if __name__ == "__main__":
    test_chemistry()
