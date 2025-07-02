/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true, // TODO: change
  },
  webpack: (config, { isServer }) => {
    config.ignoreWarnings = [
      {
        module: /node_modules\/@supabase\/realtime-js/,
        message:
          /Critical dependency: the request of a dependency is an expression/,
      },
    ];

    config.plugins.push({
      apply(compiler) {
        compiler.hooks.done.tap("LogBuildModulesPlugin", (stats) => {
          const info = stats.toJson();
          if (stats.hasErrors() && Array.isArray(info.errors) && info.errors.length > 0) {
            console.error("\n\n🚨 Build Errors:");
            for (const e of info.errors) {
              console.error(e?.message || e);
            }
          }
        });
      },
    });

    // Configure better-sqlite3 for server-side code
    if (isServer) {
      config.externals.push("better-sqlite3");
    }

    return config;
  },
};

export default nextConfig;
