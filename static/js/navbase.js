// ----------------------------- search button ----------------------------- //
var searchButton = document.querySelector(".searchButton")
var searchTerm = document.querySelector(".searchTerm")

if (searchButton != null) {
    searchTerm.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission behavior
            document.querySelector('.searchButton').click(); // Simulate click on the search button
        }
        searchButton.addEventListener("click", async function() {
                // Get form data
                search(searchTerm.value);
        });
    })
}

async function search(searchTerm) {
    console.log("searching for ")
    console.log(searchTerm)

    if (searchTerm.trim() !== '') {     // Check if search term is not empty
        var url = `/search/?query=${encodeURIComponent(searchTerm)}`; // Encode search term for URL
        window.location.href = url;     // Redirect to url with the search term
    }
    // SETUP HTTP REQ FOR SEARCH BUTTON

    // let response = await fetch("/createPost", {
    //     method: "post",
    //     headers: {
    //         'Content-Type': 'application/json'
    //     },
    //     body: JSON.stringify({postText})
    // });
    // if (!response.ok) {
    //     alert("could not post, try again ฅ(^=✪ ᴥ ✪=^)ฅ")
    // } else {
    //     window.location.reload()
    // }
}