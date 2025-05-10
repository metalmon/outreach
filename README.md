# Outreach App

> **Development Status**: This application is currently in early development stage and is not yet ready for production use. Features are being actively developed and APIs may change.

A Frappe-based email outreach application with intelligent email pool management, campaign distribution capabilities, and AI-powered personalization.

## Overview

Outreach App is a powerful email outreach solution built on the Frappe framework. It provides automated email distribution, campaign management, and sender pool optimization features to help manage large-scale email outreach campaigns effectively. The application leverages artificial intelligence to enrich contact data and generate personalized email content, making your outreach campaigns more engaging and effective.

## Features

- Automated email distribution system
- Intelligent sender pool management
- Campaign-based email scheduling
- Hourly and daily email limit management
- Customizable email distribution rules
- Integration with Frappe's email queue system
- AI-powered data enrichment for contacts
- Smart email personalization using AI
- Dynamic content generation based on recipient data
- Automated A/B testing of email variations
- Flexible AI backend options (OpenRouter or local LMStudio)

## Requirements

- Python 3.x
- Frappe Framework
- MySQL/MariaDB
- AI Backend (choose one):
  - OpenRouter API key
  - LMStudio (for local deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/outreach_app.git
cd outreach_app
```

2. Install the package:
```bash
pip install -e .
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The application can be configured through Frappe's configuration system. Key configuration options include:

- Email distribution rules
- Campaign settings
- Sender pool management
- Rate limiting parameters
- AI personalization settings
- Data enrichment preferences
- Content generation parameters
- AI backend selection (OpenRouter/LMStudio)
- Model selection and parameters

## Usage

### Email Distribution

The app automatically handles email distribution through scheduled tasks:
- Hourly counter resets
- Daily counter resets
- Campaign email distribution (every 15 minutes)

### AI Features

The application uses AI to enhance your outreach campaigns:

1. **Data Enrichment**
   - Automatically enriches contact information
   - Identifies relevant company information
   - Finds social media profiles and professional details

2. **Email Personalization**
   - Generates personalized email content
   - Adapts tone and style based on recipient profile
   - Creates dynamic subject lines
   - Optimizes email timing based on recipient behavior

3. **Content Optimization**
   - A/B testing of different email variations
   - Performance analysis and recommendations
   - Continuous learning from campaign results

### AI Backend Options

1. **OpenRouter Integration**
   - Access to multiple AI models
   - Cost-effective API usage
   - Flexible model selection
   - Automatic fallback options

2. **LMStudio Local Deployment**
   - Complete data privacy
   - No API costs
   - Custom model fine-tuning
   - Offline operation capability

### Commands

The app provides several CLI commands for managing email distribution:

```bash
bench --site your-site.com distribute-emails
```

## Project Structure

```
outreach_app/
├── api/            # API endpoints and handlers
├── commands/       # CLI commands
├── doctype/        # Document type definitions
├── utils/          # Utility functions
│   ├── email_distribution.py  # Email distribution logic
│   └── ai_services.py        # AI integration services
│       ├── openrouter.py     # OpenRouter integration
│       └── lmstudio.py       # LMStudio integration
├── app.py          # Main application configuration
├── hooks.py        # Frappe hooks and events
└── __init__.py     # Package initialization
```

## Development

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please contact your.email@example.com or open an issue in the repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
