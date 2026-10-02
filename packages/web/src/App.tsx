import { useState } from "react";
import { Layout } from "./components/Layout";
import { ReviewQueue } from "./components/ReviewQueue";
import { Statistics } from "./components/Statistics";

export type Page = "review" | "stats";

function App() {
  const [page, setPage] = useState<Page>("review");

  return (
    <Layout currentPage={page} onNavigate={setPage}>
      {page === "review" && <ReviewQueue />}
      {page === "stats" && <Statistics />}
    </Layout>
  );
}

export default App;
