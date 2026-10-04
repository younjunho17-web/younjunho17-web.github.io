source "https://rubygems.org"

# 로컬 미리보기용. 배포는 GitHub Action(actions/jekyll-build-pages)이 하며
# 이 Gemfile을 쓰지 않는다. 아래 버전은 Pages 환경(Jekyll 3.10)에 맞춘 것.
# (github-pages gem은 Ruby 4 미지원이라 직접 지정)
gem "jekyll", "~> 3.10.0"
gem "kramdown-parser-gfm"
group :jekyll_plugins do
  gem "jekyll-feed"
  gem "jekyll-paginate"
end
gem "webrick"
# Ruby 3.4+에서 표준 라이브러리에서 빠진 것들
gem "csv"
gem "base64"
gem "bigdecimal"
gem "logger"
