# HS Pak Sim Database API

A Flask-based REST API for Pakistan mobile number and CNIC information lookup.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

## ✨ Features

- ✅ **Mobile Number Lookup** - Pakistan mobile numbers (923XX formats)
- ✅ **CNIC Lookup** - 13-digit CNIC information
- ✅ **RESTful API** - GET & POST endpoints
- ✅ **JSON Responses** - Clean, structured JSON output
- ✅ **Error Handling** - Proper HTTP status codes (400, 404, 500)
- ✅ **Rate Limiting** - Prevents abuse
- ✅ **CORS Support** - Cross-origin requests allowed
- ✅ **Health Check** - Service monitoring endpoint

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/hs-pak-sim-info-api.git
cd hs-pak-sim-info-api

# Install dependencies
pip install -r requirements.txt

# Run locally
python paksimInfo.py
