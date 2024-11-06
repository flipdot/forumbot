from datetime import datetime, date

import matplotlib.pyplot as plt
import pandas as pd
import yaml


def plot_gantt_chart(
    voucher, start_date: date, end_date: date, exhausted_at: datetime | None = None
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    data = []
    for i, voucher in enumerate(voucher):
        history = voucher["history"]
        last_end = start_date
        for j, entry in enumerate(
            sorted(history, key=lambda x: datetime.fromisoformat(x["received_at"]))
        ):
            start = pd.to_datetime(entry["received_at"])
            if j + 1 < len(history):
                end = pd.to_datetime(history[j + 1]["received_at"])
            else:
                end = pd.to_datetime("now")

            if entry["persons"] > 1:
                extra_persons = f" + {entry['persons'] - 1}"
            else:
                extra_persons = ""
            data.append(
                {
                    "voucher_id": f"#{i + 1}",
                    "username": entry["username"],
                    "text": f"{entry['username']}{extra_persons}",
                    "start": start,
                    "end": end,
                }
            )
            last_end = end
        days_left = (end_date - last_end).days
        data.append(
            {
                "voucher_id": f"#{i + 1}",
                "username": "",
                "text": f"noch max {days_left} Tage",
                "start": last_end,
                "end": end_date,
            }
        )

    # Convert data to DataFrame and process dates
    df = pd.DataFrame(data)
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["duration"] = df["end"] - df["start"]

    # Unique colors for each user
    user_colors = {
        user: plt.cm.tab20(i) for i, user in enumerate(df["username"].unique())
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    # Loop over each voucher and each record within each voucher
    voucher_ids = df["voucher_id"].unique()[::-1]
    for voucher_id in voucher_ids:
        voucher_data = df[df["voucher_id"] == voucher_id]
        for _, row in voucher_data.iterrows():
            start = row["start"]
            duration = row["duration"]
            color = user_colors[row["username"]]

            ax.barh(
                voucher_id,
                duration,
                left=start.to_pydatetime(),
                color=color,
                edgecolor="black",
            )
            ax.text(
                start.to_pydatetime() + duration / 2,
                voucher_id,
                row["text"],
                va="center",
                ha="center",
                color="black",
                fontsize=8,
                weight="bold",
            )

    if exhausted_at:
        exhausted_at = pd.to_datetime(exhausted_at)
        ax.axvline(exhausted_at, color="red", linestyle="--", label="Exhausted at")
        ax.text(
            exhausted_at,
            len(voucher_ids),
            "Kontingent erschöpft",
            va="center",
            ha="center",
            color="red",
            fontsize=12,
            weight="bold",
        )

    ax.set_title("Voucherstats")
    ax.set_yticks(range(len(voucher_ids)))
    ax.set_yticklabels(voucher_ids)
    date_range = pd.date_range(start_date, end_date)

    ax.set_xticks(date_range)
    ax.set_xticklabels(date_range.strftime("%Y-%m-%d"), rotation=90)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    with open("new_storage.yaml") as f:
        store = yaml.safe_load(f.read())

    fig = plot_gantt_chart(
        store["voucher"],
        start_date=date(2024, 10, 22),
        end_date=date(2024, 11, 11),
        exhausted_at=datetime(2024, 11, 5, 12, 26),
    )
    fig.show()
