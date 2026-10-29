document.addEventListener("DOMContentLoaded", () => {
    const tablebody = document.getElementById("item-list");
    const totalCountElem = document.getElementById("total-count");

    tablebody.addEventListener("click", async (event) => {
        const delButton = event.target.closest(".js-button");
        if (!delButton) return;

        const itemId = delButton.dataset.itemId;
        if(!confirm('Delete item #${itemId}')) return;

        try {
            const response = await fetch(`/items/${itemId}`, {
                method: "DELETE", });
            if (!response.ok) {
                const targetRow = document.getElementById(`row-${itemId}`);
                targetRow.remove();
                if (totalCountElem) {
                    const currentCount = parseInt(totalCountElem.textContent, 10);
                    totalCountElem.textContent = currentCount - 1;
                }
            } else {
                alert("Failed to delete item. Please try again.")
            }
        } catch (error) {
            console.error("Error deleting item:", error);
        }
    })
)