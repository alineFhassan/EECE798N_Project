document.addEventListener("DOMContentLoaded", () => {
    const pdfForm = document.getElementById("csvForm");
    const pdfFileInput = document.getElementById("csvFile");
    const pdfAlert = document.getElementById("csvAlert");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
  
    if (pdfForm) {
      // File input change handler
      pdfFileInput.addEventListener("change", (e) => {
        resetUI();
  
        const file = e.target.files[0];
        if (!file) return;
  
        const isPDF = file.name.endsWith(".pdf") || file.type === "application/pdf";
  
        if (!isPDF) {
          showAlert("error", "Please upload a valid PDF file");
          return;
        }
  
        // Show file info
        fileInfo.classList.remove("hidden");
        fileName.textContent = file.name;
        fileSize.textContent = `(${formatFileSize(file.size)})`;
  
        showAlert("success", "PDF file is ready to be uploaded.");
      });
  
      // Form submission
      pdfForm.addEventListener("submit", (e) => {
        e.preventDefault();
  
        const file = pdfFileInput.files[0];
        if (!file) {
          showAlert("error", "Please select a PDF file to upload");
          return;
        }
  
        console.log("PDF uploaded:", file);
        showAlert("success", "Your PDF has been uploaded successfully");
      });
    }
  
    function resetUI() {
      pdfAlert.className = "alert hidden";
      fileInfo.classList.add("hidden");
    }
  
    function showAlert(type, message) {
      pdfAlert.textContent = message;
      pdfAlert.className = type === "success" ? "alert alert-success" : "alert alert-danger";
    }
  
    function formatFileSize(bytes) {
      if (bytes < 1024) return bytes + " bytes";
      else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
      else return (bytes / 1048576).toFixed(1) + " MB";
    }
  });
  