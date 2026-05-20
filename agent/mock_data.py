import random
from datetime import datetime, timedelta


def generate_mock_posts(count: int = 20) -> list[dict]:
    authors = [
        {"name": "Daria Yakovleva", "headline": "Founder @ TeleBot · Telegram AI agent, 300K MAU"},
        {"name": "Alex Panchenko", "headline": "Partner @ Runa Capital · Deep Tech VC"},
        {"name": "Sarah Chen", "headline": "Head of AI @ Stripe · Ex-Google DeepMind"},
        {"name": "Mikhail Voronov", "headline": "CTO @ Yandex Cloud · Building the future of infra"},
        {"name": "Elena Kosova", "headline": "CEO @ SkillFactory · EdTech · 500K students"},
        {"name": "James Liu", "headline": "Staff Engineer @ OpenAI · GPT team"},
        {"name": "Anna Petrova", "headline": "Product Lead @ Notion · AI features"},
        {"name": "Mark Zubov", "headline": "Serial Entrepreneur · 3 exits · Angel investor"},
        {"name": "Lisa Wang", "headline": "ML Engineer @ Meta · PyTorch core team"},
        {"name": "Dmitry Karpov", "headline": "Founder @ CodeReview.ai · YC W24"},
        {"name": "Natalie Torres", "headline": "VP Engineering @ Figma · Design tools"},
        {"name": "Oleg Smirnov", "headline": "Head of Growth @ Miro · PLG advocate"},
    ]

    posts_templates = [
        {
            "text": "AI agents are the new SaaS. Here's why:\n\n1. Zero learning curve\n2. Pay per outcome, not per seat\n3. They improve with every interaction\n\nWe've seen 40% of our support tickets resolved by agents this quarter. The shift is real.",
            "media_type": "text",
            "topic_hint": "AI agents",
            "engagement_mult": 2.5,
        },
        {
            "text": "Just shipped our first Claude-powered feature. The Agent SDK made it surprisingly easy to build a multi-step workflow that:\n\n- Reads customer tickets\n- Classifies urgency\n- Drafts responses\n- Routes to the right team\n\nFrom idea to production in 3 days.",
            "media_type": "text",
            "topic_hint": "AI development",
            "engagement_mult": 2.0,
        },
        {
            "text": "Unpopular opinion: most AI startups are just thin wrappers around API calls.\n\nThe real moat is in workflow design, not model access.\n\nAgree? 👇",
            "media_type": "text",
            "topic_hint": "AI startups",
            "engagement_mult": 3.0,
        },
        {
            "text": "I quit my job at Google to build my own thing. 6 months in, here's what nobody tells you about solo founding:\n\n1. The loneliness is real\n2. Revenue > funding\n3. Ship weekly or die\n4. Your network IS your product\n5. Health first, always\n\nBest decision I ever made. Worst days are still better than my best days in corp.",
            "media_type": "image",
            "topic_hint": "career",
            "engagement_mult": 3.5,
        },
        {
            "text": "3 lessons from launching a product to 10K users in 30 days:\n\n🎯 Build for ONE person, not everyone\n📣 Launch on 5 platforms simultaneously\n🔄 Ship daily updates for the first 2 weeks\n\nThread below 🧵",
            "media_type": "carousel",
            "topic_hint": "startup growth",
            "engagement_mult": 2.2,
        },
        {
            "text": "We just raised $12M Series A to build the next generation of AI-native productivity tools.\n\nHiring: 5 engineers, 2 designers, 1 PM.\n\nDM me if you want to build the future of work.",
            "media_type": "image",
            "topic_hint": "fundraising",
            "engagement_mult": 1.8,
        },
        {
            "text": "The best technical interview question I've ever asked:\n\n'Walk me through how you'd debug a system that works perfectly in staging but fails randomly in production.'\n\nNo right answer. Tells you everything about how someone thinks.",
            "media_type": "text",
            "topic_hint": "hiring",
            "engagement_mult": 2.8,
        },
        {
            "text": "Day in my life as a remote CTO:\n\n6:00 - Wake up, no alarm\n6:30 - Deep work (code review)\n9:00 - Stand-up with EU team\n10:00 - Product sync\n12:00 - Gym\n14:00 - 1:1s\n16:00 - Strategy work\n18:00 - Family time\n\nRemote isn't about flexibility. It's about intentional structure.",
            "media_type": "image",
            "topic_hint": "remote work",
            "engagement_mult": 1.5,
        },
        {
            "text": "Hot take: RAG is already outdated.\n\nWith 1M+ context windows, you can just... put the documents in the prompt.\n\nThe chunking-embedding-retrieval pipeline adds complexity, latency, and failure modes that aren't worth it for most use cases.",
            "media_type": "text",
            "topic_hint": "AI technical",
            "engagement_mult": 2.7,
        },
        {
            "text": "Just published a comprehensive guide on building production AI agents with Claude.\n\nCovers: tool use, multi-step reasoning, error handling, evaluation, and deployment.\n\n12,000 words. Free. Link in comments.",
            "media_type": "article",
            "topic_hint": "AI development",
            "engagement_mult": 2.0,
        },
        {
            "text": "Attended an incredible AI meetup in Berlin last night.\n\n200+ people. Energy was electric. Key takeaway: the European AI ecosystem is catching up FAST.\n\nIf you're building in AI and based in EU, connect with me. Let's build together. 🇪🇺",
            "media_type": "image",
            "topic_hint": "community",
            "engagement_mult": 1.6,
        },
        {
            "text": "The 5 tools every founder should be using in 2026:\n\n1. Claude Code for development\n2. Linear for project management\n3. Notion for knowledge base\n4. Loom for async communication\n5. Figma for design\n\nWhat would you add?",
            "media_type": "carousel",
            "topic_hint": "tools",
            "engagement_mult": 1.9,
        },
        {
            "text": "I've been a VC for 10 years. Here's the #1 pattern I see in founders who succeed:\n\nThey don't pivot. They ZOOM IN.\n\nThey find the one thing that works and ruthlessly cut everything else.\n\nExecution > strategy, every single time.",
            "media_type": "text",
            "topic_hint": "VC wisdom",
            "engagement_mult": 2.4,
        },
        {
            "text": "Open source update: our AI code review tool just hit 15K GitHub stars ⭐\n\nNew in v3.0:\n- Multi-file context awareness\n- Security vulnerability detection\n- Auto-fix suggestions\n\nTry it: link in comments",
            "media_type": "image",
            "topic_hint": "open source",
            "engagement_mult": 1.7,
        },
        {
            "text": "If you're not using AI to write your LinkedIn posts yet, you're falling behind.\n\n...is what I would say if I had no integrity.\n\nYour authentic voice > any AI output. People follow people, not prompts.",
            "media_type": "text",
            "topic_hint": "personal branding",
            "engagement_mult": 2.6,
        },
        {
            "text": "Shipped a feature this week that reduced our API latency by 73%.\n\nThe fix? We stopped over-engineering.\n\nRemoved: Redis cache, message queue, 3 microservices\nReplaced with: one SQLite database and a cron job\n\nSimplicity wins. Every. Single. Time.",
            "media_type": "text",
            "topic_hint": "engineering",
            "engagement_mult": 3.2,
        },
        {
            "text": "My team just completed a 6-month migration from React to Next.js.\n\nResults:\n- 45% faster page loads\n- 30% less client-side JS\n- SEO traffic up 2.3x\n\nWas it worth the pain? Absolutely.\n\nHere's the migration playbook we used 👇",
            "media_type": "carousel",
            "topic_hint": "engineering",
            "engagement_mult": 1.8,
        },
        {
            "text": "Controversial: most 'AI strategy' consulting is just PowerPoint. Change my mind.\n\nCompanies don't need a strategy deck. They need one engineer with API access and permission to ship.\n\nThe gap isn't knowledge. It's permission.",
            "media_type": "text",
            "topic_hint": "AI strategy",
            "engagement_mult": 2.9,
        },
        {
            "text": "Grateful post 🙏\n\n5 years ago I moved to Berlin with no network, no German, and a half-baked startup idea.\n\nToday: 50-person team, profitable, and just opened our second office.\n\nTo everyone who helped along the way — thank you. You know who you are.",
            "media_type": "image",
            "topic_hint": "personal story",
            "engagement_mult": 2.1,
        },
        {
            "text": "PSA: If you're storing API keys in environment variables and calling it 'secure', we need to talk.\n\nProper secrets management in 2026:\n1. HashiCorp Vault or AWS Secrets Manager\n2. Rotate every 90 days minimum\n3. Audit access logs\n4. Zero trust by default\n\nYour .env file is not a security strategy.",
            "media_type": "text",
            "topic_hint": "security",
            "engagement_mult": 1.4,
        },
    ]

    now = datetime.now()
    posts = []

    selected = posts_templates * ((count // len(posts_templates)) + 1)
    for i in range(count):
        template = selected[i]
        author = random.choice(authors)
        base_likes = random.randint(30, 150)
        mult = template["engagement_mult"]

        posts.append({
            "url": f"https://www.linkedin.com/feed/update/urn:li:activity:{7300000000000 + i}",
            "author_name": author["name"],
            "author_headline": author["headline"],
            "text": template["text"],
            "media_type": template["media_type"],
            "likes": int(base_likes * mult),
            "comments": int(base_likes * mult * random.uniform(0.05, 0.2)),
            "reposts": int(base_likes * mult * random.uniform(0.02, 0.1)),
            "timestamp": (now - timedelta(hours=random.randint(1, 168))).isoformat(),
        })

    return posts
