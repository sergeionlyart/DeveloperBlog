// Admin page JavaScript with minimal dependencies and maximized reliability
// Simplifies client-side functionality to improve stability

document.addEventListener('DOMContentLoaded', function() {
  console.log("Admin JS loaded successfully");
  
  // Basic slug generation - minimal features to reduce complexity
  try {
    const titleInput = document.getElementById('title');
    const slugInput = document.getElementById('slug');
    
    if (titleInput && slugInput) {
      titleInput.addEventListener('input', function() {
        // Only auto-generate if slug field is empty
        if (!slugInput.value) {
          const slug = titleInput.value
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')  // Remove special chars
            .replace(/\s+/g, '-')      // Replace spaces with hyphens
            .replace(/-+/g, '-')       // Replace multiple hyphens with single hyphen
            .trim();
          
          slugInput.value = slug;
        }
      });
    }
  } catch (e) {
    console.error("Error in slug generation:", e);
  }

  // Confirm delete operations - essential for data protection
  try {
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
          e.preventDefault();
        }
      });
    });
  } catch (e) {
    console.error("Error in delete confirmation:", e);
  }
  
  // Category edit functionality - simplified
  try {
    const editCategoryButtons = document.querySelectorAll('.edit-category-btn');
    
    editCategoryButtons.forEach(button => {
      button.addEventListener('click', function() {
        const categoryId = this.getAttribute('data-category-id');
        const categoryName = this.getAttribute('data-category-name');
        const categoryDesc = this.getAttribute('data-category-desc') || '';
        
        const idField = document.getElementById('edit-category-id');
        const nameField = document.getElementById('edit-category-name');
        const descField = document.getElementById('edit-category-description');
        
        if (idField) idField.value = categoryId;
        if (nameField) nameField.value = categoryName;
        if (descField) descField.value = categoryDesc;
      });
    });
  } catch (e) {
    console.error("Error in category editing:", e);
  }
  
  // Tag edit functionality - simplified
  try {
    const editTagButtons = document.querySelectorAll('.edit-tag-btn');
    
    editTagButtons.forEach(button => {
      button.addEventListener('click', function() {
        const tagId = this.getAttribute('data-tag-id');
        const tagName = this.getAttribute('data-tag-name');
        
        const idField = document.getElementById('edit-tag-id');
        const nameField = document.getElementById('edit-tag-name');
        
        if (idField) idField.value = tagId;
        if (nameField) nameField.value = tagName;
      });
    });
  } catch (e) {
    console.error("Error in tag editing:", e);
  }
});
