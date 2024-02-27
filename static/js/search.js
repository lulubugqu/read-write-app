document.addEventListener('DOMContentLoaded', function() {
    // Retrieve previous form data from local storage
    const savedFilters = JSON.parse(localStorage.getItem('savedFilters'));

    // If there are saved filters, populate the form fields with them
    if (savedFilters) {
        Object.keys(savedFilters).forEach(key => {
            const checkbox = document.getElementById(key);
            if (checkbox) {
                checkbox.checked = savedFilters[key] === "On";
            }
        });

        const chapterRange = document.querySelector('input[name="chapterRange"]');
        if (chapterRange) {
            chapterRange.value = savedFilters['chapterRange'];
            document.getElementById('rangeValue').innerText = savedFilters['chapterRange'];
        }

        const likeRange = document.querySelector('input[name="range"]');
        if (likeRange) {
            likeRange.value = savedFilters['range'];
            document.getElementById('likeValue').innerText = savedFilters['range'];
        }

        const tagsInput = document.getElementById('tags');
        if (tagsInput) {
            tagsInput.value = savedFilters['tags'];
        }
    }

    // Event listener to save form data to local storage on form submission
    document.getElementById('save_search_filters').addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = {
            'chapterRange': document.querySelector('input[name="chapterRange"]').value,
            'range': document.querySelector('input[name="range"]').value,
            'tags': document.getElementById('tags').value
        };

        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            formData[checkbox.id] = checkbox.checked ? "On" : "Off";
        });

        localStorage.setItem('savedFilters', JSON.stringify(formData));

        this.submit();
    });
});