/**
 * CampusFind - Client-side Utilities
 * Author: Amishka Sisodiya
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Auto-dismiss alerts after 6 seconds
  const flashAlerts = document.querySelectorAll('.alert-dismissible');
  flashAlerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });

  // 2. Photo upload size client check (Max 5 MB) + instant preview
  const photoInput = document.getElementById('photoInput');
  const photoPreview = document.getElementById('photoPreview');
  const previewImg = document.getElementById('previewImg');

  if (photoInput) {
    photoInput.addEventListener('change', function (e) {
      const file = this.files[0];
      if (file) {
        // 5 MB limit check: 5 * 1024 * 1024 = 5242880 bytes
        if (file.size > 5242880) {
          alert('Warning: The selected image exceeds 5 MB. Please choose a smaller photo.');
          this.value = '';
          if (photoPreview) photoPreview.classList.add('d-none');
          return;
        }

        // Preview rendering
        if (photoPreview && previewImg) {
          const reader = new FileReader();
          reader.onload = function (event) {
            previewImg.src = event.target.result;
            photoPreview.classList.remove('d-none');
          };
          reader.readAsDataURL(file);
        }
      }
    });
  }

  // 3. Dynamic Post Form (Switch between Lost and Found fields)
  const typeRadios = document.querySelectorAll('input[name="type"]');
  const foundVerificationGroup = document.getElementById('foundVerificationGroup');
  const verificationQuestionInput = document.getElementById('verification_question');
  const verificationAnswerInput = document.getElementById('verification_answer');

  function updateTypeFields(selectedType) {
    if (!foundVerificationGroup) return;
    if (selectedType === 'found') {
      foundVerificationGroup.classList.remove('d-none');
      if (verificationQuestionInput) verificationQuestionInput.required = true;
      if (verificationAnswerInput) verificationAnswerInput.required = true;
    } else {
      foundVerificationGroup.classList.add('d-none');
      if (verificationQuestionInput) verificationQuestionInput.required = false;
      if (verificationAnswerInput) verificationAnswerInput.required = false;
    }
  }

  if (typeRadios.length > 0) {
    typeRadios.forEach(radio => {
      radio.addEventListener('change', function () {
        updateTypeFields(this.value);
      });
      if (radio.checked) {
        updateTypeFields(radio.value);
      }
    });
  }

  // 4. Default today's date for date inputs if empty
  const dateInput = document.getElementById('itemDate');
  if (dateInput && !dateInput.value) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }
});
