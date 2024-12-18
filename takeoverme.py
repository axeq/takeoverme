import argparse
import asyncio
import aiohttp
import dns.asyncresolver
import json

async def get_cname(subdomain):
    try:
        resolver = dns.asyncresolver.Resolver()
        answers = await resolver.resolve(subdomain, 'CNAME')
        for rdata in answers:
            return str(rdata.target)
    except dns.resolver.NoAnswer:
        return "No CNAME record found."
    except dns.resolver.NXDOMAIN:
        return "Domain does not exist."
    except Exception as e:
        return f"Error: {e}"

async def check_url(session, url, retries=3):
    for attempt in range(retries):
        for protocol in ("https://", "http://"):
            try:
                async with session.get(f"{protocol}{url}", timeout=5) as response:
                    return response.status
            except Exception:
                continue
        await asyncio.sleep(1)
    return None

async def process_subdomain(session, subdomain, semaphore, verbose, output_file, fingerprints):
    async with semaphore:
        status_code = await check_url(session, subdomain)
        if status_code == 404:
            cname = await get_cname(subdomain)
            if cname:
                for fingerprint in fingerprints:
                    if fingerprint in cname:
                        result = f"TAKEOVER POSSIBLE AT {subdomain} (CNAME: {cname})"
                        if verbose:
                            print(result)
                        with open(output_file, 'a') as f:
                            f.write(result + "\n")
                        break
        elif status_code:
            if verbose:
                print(f"ACTIVE DOMAIN: {subdomain} (Status: {status_code})")
        else:
            if verbose:
                pass

async def main():
    print(r"""
_________ _______  _        _______  _______           _______  _______    _______  _______ 
\__   __/(  ___  )| \    /\(  ____ \(  ___  )|\     /|(  ____ \(  ____ )  (       )(  ____ \
   ) (   | (   ) ||  \  / /| (    \/| (   ) || )   ( || (    \/| (    )|  | () () || (    \/
   | |   | (___) ||  (_/ / | (__    | |   | || |   | || (__    | (____)|  | || || || (__    
   | |   |  ___  ||   _ (  |  __)   | |   | |( (   ) )|  __)   |     __)  | |(_)| ||  __)   
   | |   | (   ) ||  ( \ \ | (      | |   | | \ \_/ / | (      | (\ (     | |   | || (      
   | |   | )   ( ||  /  \ \| (____/\| (___) |  \   /  | (____/\| ) \ \__  | )   ( || (____/\
   )_(   |/     \||_/    \/(_______/(_______)   \_/   (_______/|/   \__/  |/     \|(_______/
                                                                                                                                           
                                                                                            
by: sweatyxull (discord) / axeq (github)
""")
    parser = argparse.ArgumentParser(description="Subdomain Takeover Detection Tool")
    parser.add_argument("-l", "--list", required=True, help="File with subdomains list")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Max number of concurrent threads (default: 10)")
    parser.add_argument("-o", "--output", required=True, help="Output file for results")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output during execution")

    args = parser.parse_args()

    with open(args.list, 'r') as f:
        urls = [line.strip() for line in f.readlines()]

    with open("fingerprints.json", 'r') as f:
        fingerprints_data = json.load(f)
        fingerprints = fingerprints_data["fingerprints"]

    semaphore = asyncio.Semaphore(args.threads)
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_subdomain(session, url, semaphore, args.verbose, args.output, fingerprints) for url in urls]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())