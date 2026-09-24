


def RRF(similar_data, key_word_data, k: int = 60):

    similar_list = []
    for rank, data in enumerate(similar_data,start=1):
        similar_list.append((rank, data))

    keyword_list = []
    for rank, data in enumerate(key_word_data, start=1):
        keyword_list.append((rank, data))


    docs = similar_list + keyword_list
    docs_rank = []
    for i in docs:
        docs_rank.append((i[0],i[1][0]))


    rrf_scores = {}

    for rank, doc_id in docs_rank:
        score = 1 / (k + rank)

        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = 0

        rrf_scores[doc_id] += score

    # Sort documents according to their RRF score
    sorted_by_rrf_score = sorted(
        rrf_scores.items(),
        key = lambda x: x[1],
        reverse=True
    )

    content = []
    for doc_id, rrf_score in sorted_by_rrf_score:

        for _, data in docs:

            if data[0] == doc_id:

                content.append({
                    "content": data[1],
                    "page_number": data[2],
                    "source": data[3],
                    "score": rrf_score
                })

                break

    print("RRF is done")

    return content


