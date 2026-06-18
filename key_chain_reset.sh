#!/bin/bash

printf "host=git-codecommit.us-east-1.amazonaws.com\nprotocol=https\n" | git credential-osxkeychain erase
echo "CodeCommit keychain credentials cleared"
