#!/bin/bash
cloudron-docker-builder add-config \
  --repo https://github.com/igmarketing/flawless-dashboard \
  --branch main \
  --dockerfile Dockerfile \
  --image-name my.flawlessmarketing.com:5000/dashboard \
  --tag latest \
  --registry registry.flawlessmarketing.com:5000 \
  --registry-username dl.lobo@hotmaill.com \
  --registry-password h9jZk76!JADEQxb
