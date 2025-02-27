// Admin page JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
  console.log("Admin JS loaded successfully");
  
  /* SimpleMDE initialization temporarily disabled
  const contentTextarea = document.getElementById('content');
  if (contentTextarea) {
    const simplemde = new SimpleMDE({ 
      element: contentTextarea,
      spellChecker: false,
      autosave: {
        enabled: true,
        unique_id: "article_content",
        delay: 1000,
      },
      toolbar: ["bold", "italic", "heading", "|", 
                "code", "quote", "unordered-list", "ordered-list", "|",
                "link", "image", "table", "|",
                "preview", "side-by-side", "fullscreen", "|",
                "guide"],
      renderingConfig: {
        codeSyntaxHighlighting: true,
      }
    });
  }
  */

  // Auto-generate slug from title
  const titleInput = document.getElementById('title');
  const slugInput = document.getElementById('slug');
  
  if (titleInput && slugInput) {
    titleInput.addEventListener('input', function() {
      // Only auto-generate if the slug field is empty or hasn't been manually edited
      if (!slugInput.dataset.edited) {
        const slug = titleInput.value
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')  // Remove special chars
          .replace(/\s+/g, '-')      // Replace spaces with hyphens
          .replace(/-+/g, '-')       // Replace multiple hyphens with single hyphen
          .trim();
        
        slugInput.value = slug;
      }
    });
    
    // Mark the slug field as manually edited when user types in it
    slugInput.addEventListener('input', function() {
      slugInput.dataset.edited = 'true';
    });
  }

  // Auto-generate meta title and description if empty
  const metaTitleInput = document.getElementById('meta_title');
  const metaDescInput = document.getElementById('meta_description');
  const summaryInput = document.getElementById('summary');
  
  if (titleInput && metaTitleInput) {
    titleInput.addEventListener('change', function() {
      if (!metaTitleInput.value) {
        metaTitleInput.value = titleInput.value;
      }
    });
  }
  
  if (summaryInput && metaDescInput) {
    summaryInput.addEventListener('change', function() {
      if (!metaDescInput.value) {
        // Limit to 160 chars for meta description
        metaDescInput.value = summaryInput.value.substring(0, 160);
      }
    });
  }

  // Confirm delete operations
  const deleteButtons = document.querySelectorAll('.delete-confirm');
  deleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
        e.preventDefault();
      }
    });
  });
  
  // Category edit modal functionality
  const editCategoryButtons = document.querySelectorAll('.edit-category-btn');
  
  editCategoryButtons.forEach(button => {
    button.addEventListener('click', function() {
      const categoryId = this.dataset.categoryId;
      const categoryName = this.dataset.categoryName;
      const categoryDesc = this.dataset.categoryDesc || '';
      
      document.getElementById('edit-category-id').value = categoryId;
      document.getElementById('edit-category-name').value = categoryName;
      document.getElementById('edit-category-description').value = categoryDesc;
    });
  });
  
  // Tag edit modal functionality
  const editTagButtons = document.querySelectorAll('.edit-tag-btn');
  
  editTagButtons.forEach(button => {
    button.addEventListener('click', function() {
      const tagId = this.dataset.tagId;
      const tagName = this.dataset.tagName;
      
      document.getElementById('edit-tag-id').value = tagId;
      document.getElementById('edit-tag-name').value = tagName;
    });
  });
  
  // Handle form validation
  const forms = document.querySelectorAll('.needs-validation');
  
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      
      form.classList.add('was-validated');
    }, false);
  });
  
  // Toggle publish status
  const publishToggle = document.getElementById('published');
  const publishStatus = document.getElementById('publish-status');
  
  if (publishToggle && publishStatus) {
    publishToggle.addEventListener('change', function() {
      if (this.checked) {
        publishStatus.textContent = 'Published';
        publishStatus.classList.remove('badge-secondary');
        publishStatus.classList.add('badge-success');
      } else {
        publishStatus.textContent = 'Draft';
        publishStatus.classList.remove('badge-success');
        publishStatus.classList.add('badge-secondary');
      }
    });
  }
});
