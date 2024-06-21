# Odds Comparison Tool

## What is this
This tool compares FanDuel odds for NBA Basketball or MLB Baseball to Pinnacle Sportsbook Odds. It uses [The Odds API](https://the-odds-api.com/liveapi/guides/v4/) to retrieve this data. The goal is to find more favorable odds on FanDuel compared to a lower vig book like Pinnacle.

## Features
- Fetches odds from The Odds API.
- Compares odds between FanDuel and Pinnacle.
- Identifies valuable betting lines.

## Installation

1. **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd pinnacle
    ```

2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3. **Set up your configuration in `data/config.json`.**
   - Ensure you have your API key from The Odds API.

4. **Run the application:**
    ```bash
    python run.py
    ```

## Usage

1. **Navigate to the homepage:**
   Open a web browser and go to `http://127.0.0.1:5000`.

2. **View and compare odds:**
   Select the sport from the tabs to view the odds comparison between FanDuel and Pinnacle.

## Future Considerations
1. Create slider for to turn live games on and off.
2. Data analysis on lowest average vig sportsbook for each sport across all bookmakers. 
3. Implement other American Sportsbooks and compare the best odds to FanDuel.
4. Implement Player Props (Potentially).
5. Create into a recurring refresh live system.
## Contributing

Feel free to open issues or submit pull requests for improvements and new features.

## License

This project is licensed under the MIT License.
