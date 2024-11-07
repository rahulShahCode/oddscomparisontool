document.addEventListener('DOMContentLoaded', (event) => {
    const liveToggle = document.getElementById('live-toggle');
    const betterValueToggle = document.getElementById('better-value-toggle'); // New toggle for better value filter
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    // Function to convert New York time to UTC
    function convertToUTC(newYorkTime) {
        let nyDate = new Date(newYorkTime.replace("Start Time: ", "") + ' GMT-0400'); // Adjust for EDT or EST as needed
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

    // Function to filter and show only the game cards that contain better value
    function filterBetterValueCards() {
        const gameCards = document.querySelectorAll(".game-card");

        gameCards.forEach(game => {
            const betterValueElements = game.querySelectorAll(".better-value");

            if (betterValueToggle.checked) {
                // Show game card only if it contains a "better-value" element
                if (betterValueElements.length > 0) {
                    game.style.display = ''; // Show the game card
                } else {
                    game.style.display = 'none'; // Hide the game card
                }
            } else {
                game.style.display = ''; // Show all game cards if toggle is unchecked
            }
        });
    }

    // Dark mode toggle functionality
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    function toggleDarkMode() {
        if (darkModeToggle.checked) {
            setTheme('dark');
        } else {
            setTheme('light');
        }
    }

    // Check for saved theme preference or prefer-color-scheme
    const savedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    if (savedTheme) {
        setTheme(savedTheme);
        darkModeToggle.checked = savedTheme === 'dark';
    } else if (prefersDarkScheme.matches) {
        setTheme('dark');
        darkModeToggle.checked = true;
    }

    // Event listener for dark mode toggle
    darkModeToggle.addEventListener('change', toggleDarkMode);

    // Event listener for system theme changes
    prefersDarkScheme.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            setTheme(newTheme);
            darkModeToggle.checked = e.matches;
        }
    });

    // Event listener for the live game toggle switch
    liveToggle.addEventListener('change', () => {
        updateGameVisibility();
        localStorage.setItem('liveToggle', liveToggle.checked);
    });

    // Event listener for the better value toggle switch
    betterValueToggle.addEventListener('change', () => {
        filterBetterValueCards();
        localStorage.setItem('betterValueToggle', betterValueToggle.checked);
    });

    // Set the initial state of the live game toggle based on localStorage
    const liveToggleState = localStorage.getItem('liveToggle');
    if (liveToggleState === 'true') {
        liveToggle.checked = true;
    } else {
        liveToggle.checked = false;
    }

    // Set the initial state of the better value toggle based on localStorage
    const betterValueToggleState = localStorage.getItem('betterValueToggle');
    if (betterValueToggleState === 'true') {
        betterValueToggle.checked = true;
    } else {
        betterValueToggle.checked = false;
    }

    // Initial check for game visibility on page load
    updateGameVisibility();
    filterBetterValueCards();

    // ===================== Odds Comparison Logic =====================

    function emphasizeBetterValue() {
        const games = document.querySelectorAll(".game-card"); // Each game card

        games.forEach(game => {
            const markets = game.querySelectorAll(".inline-market"); // All markets (Spreads, Moneyline, etc.)

            markets.forEach(market => {
                const marketType = market.querySelector("h6").textContent.trim(); // "Spreads", "Moneyline", etc.
                const columns = market.querySelectorAll(".col-md-6");

                if (columns.length === 4) {
                    // Extract the odds and point values
                    const firstColumnText = columns[0].querySelector("span").textContent;
                    const fourthColumnText = columns[3].querySelector("span").textContent;

                    // Moneyline logic
                    if (marketType === "Moneyline") {
                        const [, team1Odds] = parseTeamOdds(firstColumnText);
                        const [, team2Odds] = parseTeamOdds(fourthColumnText);

                        if (parseFloat(team1Odds) > parseFloat(team2Odds)) {
                            columns[0].classList.add("better-value");
                        }
                    }
                    // Spread logic
                    else if (marketType === "Spreads") {
                        const [team1PointValue, team1SpreadOdds] = parseSpread(firstColumnText);
                        const [team2PointValue, team2SpreadOdds] = parseSpread(fourthColumnText);

                        if (parseFloat(team1PointValue) > parseFloat(team2PointValue)) {
                            columns[0].classList.add("better-value");
                        } else if (parseFloat(team1PointValue) === parseFloat(team2PointValue) &&
                            parseFloat(team1SpreadOdds) > parseFloat(team2SpreadOdds)) {
                            columns[0].classList.add("better-value");
                        }
                    }
                    // Totals logic
                    else if (marketType === "Totals") {
                        const [type1, pointValue1, odds1] = parseTotals(firstColumnText);
                        const [type2, pointValue2, odds2] = parseTotals(fourthColumnText);

                        if ((type1 === "Over" && parseFloat(pointValue1) < parseFloat(pointValue2)) ||
                            (type1 === "Under" && parseFloat(pointValue1) > parseFloat(pointValue2))) {
                            columns[0].classList.add("better-value");
                        } else if (parseFloat(pointValue1) === parseFloat(pointValue2) && parseFloat(odds1) > parseFloat(odds2)) {
                            columns[0].classList.add("better-value");
                        }
                    }
                }
            });
        });
    }

    // Utility function to parse team name and odds (for Moneyline)
    function parseTeamOdds(text) {
        const parts = text.split(":");
        return [parts[0].trim(), parts[1].trim()];
    }

    // Utility function to parse spread point value and odds
    function parseSpread(text) {
        const parts = text.split(":");  // Split into team/point value and odds
        const matchFound = parts[0].match(/[\+\-]?\d+(\.\d+)?/)  
        if(matchFound === null)
            return ["-10000", "-100"]  // Placeholder values in case parsing fails
        const pointValue = matchFound[0]
        const odds = parts[1].trim();  // Extract the odds after the colon
        return [pointValue.trim(), odds.trim()];
    }

    // Utility function to parse totals (Over/Under) point value and odds
    function parseTotals(text) {
        let parts = text.split(":");
        const odds = parts[1].trim(); 
        parts = parts[0].split(" ");
        
        return [parts[0].trim(), parts[1].trim(), odds];  // [Over/Under, pointValue, odds]
    }

    emphasizeBetterValue(); // Run the comparison and emphasize better values
});
