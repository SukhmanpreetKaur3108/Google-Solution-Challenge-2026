# PoF-AI — Monthly Cost Estimate (Low Traffic / Demo)

Target: **under $50/month** for demo/hackathon traffic.

---

## Assumptions
- 1,000 scoring requests / month
- Average certificate: 5 engine calls, ~2s compute
- All Cloud Run services scale to zero when idle
- Vertex AI endpoint: 1 replica, n1-standard-2

---

## Line-Item Breakdown

| Service | Config | Est. Monthly Cost |
|---------|--------|-------------------|
| **Cloud Run — backend** | 2 CPU / 2 GB, 1000 req × 2s, scale-to-zero | ~$2.00 |
| **Cloud Run — log service** | 1 CPU / 512 MB, 1000 req × 0.5s | ~$0.50 |
| **Vertex AI Endpoint** | n1-standard-2, 0 hrs idle (delete after demo) | ~$0 (delete) |
| **Vertex AI Predictions** | 1000 predictions + 10,000 probe calls | ~$1.00 |
| **Firestore** | 10,000 reads + 2,000 writes | ~$0.10 |
| **Cloud Storage** | 1 GB stored (evidence + log) | ~$0.02 |
| **Cloud KMS** | 2 keys × 2,000 sign ops | ~$0.20 |
| **Secret Manager** | 2 secrets, 1,000 access ops | ~$0.04 |
| **Gemini API** | 1000 req × 500 tokens in/out (gemini-1.5-pro) | ~$7.50 |
| **Firebase Hosting** | Spark plan (free tier) | $0.00 |
| **BigQuery** | 1 GB queried/month | ~$0.00 (free tier) |
| **Artifact Registry** | 2 images × ~1 GB | ~$0.20 |
| **Cloud Build** | 10 builds × 10 min | ~$0.00 (free tier) |
| **Cloud Logging** | < 50 GB/month | ~$0.00 (free tier) |
| **Terraform state (GCS)** | Minimal | ~$0.01 |

---

## Total Estimate

| Scenario | Monthly Cost |
|----------|-------------|
| **Demo / hackathon (1K requests)** | **~$12** |
| **Light production (10K requests)** | **~$35** |
| **Medium production (100K requests)** | **~$180** |

---

## Cost Reduction Tips
1. **Delete Vertex AI Endpoint when not demoing** — saves ~$50/month for an n1-standard-2 node
2. **Use `gemini-1.5-flash`** instead of `gemini-1.5-pro` for adversarial engine → ~5× cheaper
3. **Cloud Run scale-to-zero** is already configured — no idle costs
4. **Firebase Hosting Spark plan** is completely free for hackathon traffic
5. **Commit a model artifact to GCS** and use Vertex AI Batch Prediction instead of an always-on endpoint

---

## Notes
- Prices are approximate USD, us-central1 region, April 2026
- Vertex AI endpoint cost dominates if left running — **shut it down after the demo**
- Full production deployment at scale would need a proper cost model
