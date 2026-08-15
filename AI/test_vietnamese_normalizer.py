from vietnamese_normalizer import (
    display_label,
    display_pipe_values,
    normalize_avoid_terms,
    normalize_text,
    safety_tag_for_avoid_key,
)


def main():
    samples = [
        "đau gối, lưng dưới, tay sau",
        "cơ vai; đùi trước; bắp chân",
        "ngực và xô",
        "dau khop goi / dau vai",
    ]
    for sample in samples:
        print(sample, "=>", normalize_avoid_terms(sample))

    print("normalize:", normalize_text("Đau lưng dưới"))
    print("muscles:", display_pipe_values("pectoralis_major|triceps_brachii"))
    print("goal:", display_label("hypertrophy", "goal"))
    print("difficulty:", display_label("beginner", "difficulty"))
    print("safety:", safety_tag_for_avoid_key("knee"))


if __name__ == "__main__":
    main()
