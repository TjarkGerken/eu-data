import ImageAdmin from "@/components/image-admin";

export default function AdminImagesPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Climate Data Image Management</h1>
        <p className="text-muted-foreground mt-2">
          Upload, manage, and monitor climate visualization images stored in
          Vercel Blob Storage CDN.
        </p>
      </div>

      <ImageAdmin />
    </div>
  );
}
