document.addEventListener('DOMContentLoaded', (event) => {
    const liveToggle = document.getElementById('live-toggle');

    // Function to convert New York time to UTC
    function convertToUTC(newYorkTime) {
        let nyDate = new Date(newYorkTime + ' GMT-0400'); // Adjust for EDT or EST as needed
        return nyDate.toISOString();
    }

    // Function to check if the game is live
    function isGameLive(gameStartTime) {
        let currentTime = new Date().toISOString();
        return currentTime >= gameStartTime;
    }

    // Function to update visibility of game cards based on live status
    function updateGameVisibility() {
        let gameCards = document.querySelectorAll('.game-card');

        gameCards.forEach(card => {
            let startTimeText = card.querySelector('.card-body .card-text').textContent;
            let gameStartTime = convertToUTC(startTimeText);
            if (isGameLive(gameStartTime)) {
                if (liveToggle.checked) {
                    card.style.display = ''; // Show the card
                } else {
                    card.style.display = 'none'; // Hide the card
                }
            } else {
                card.style.display = ''; // Always show non-live games
            }
        });
    }

    // Event listener for the toggle switch
    liveToggle.addEventListener('change', () => {
        updateGameVisibility();
        localStorage.setItem('liveToggle', liveToggle.checked);
    });

    // Set the initial state of the toggle based on localStorage
    const liveToggleState = localStorage.getItem('liveToggle');
    if (liveToggleState === 'true') {
        liveToggle.checked = true;
    } else {
        liveToggle.checked = false;
    }

    // Initial check for game visibility on page load
    updateGameVisibility();
});
