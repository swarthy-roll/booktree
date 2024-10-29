from dataclasses import field

class Genre:
    fiction: list = field(default_factory=lambda: ["Fiction","Fantasy","Science Fiction"
                                                    ,"High Fantasy","Epic Fantasy","Dark Fantasy"
                                                    ,"Horror","Romantasy","Steampunk"
                                                    ,"Science Fiction Fantasy","Military Fiction","Fae"
                                                    ,"Fairy Tales","Space Opera","Speculative Fiction"
                                                    ,"Urban Fantasy","Novella","Vampires","Werewolves"
                                                    ,"Shapeshifters","Dragons","Magic","Paranormal"
                                                    ,"Adult Fiction","Alternate History","Chick Lit"
                                                    ,"Crime Fiction","Dystopia","Dystopian"
                                                    ,"Graphic Novels","Historical Fantasy"
                                                    ,"Historical Fantasy","Magical Realism"
                                                    ,"Paranormal Romance","Superheroes"
                                                    ,"Time Travel","Young Adult Fantasy","Women's Fiction"])
    nonfiction: list = field(default_factory=lambda: ["Nonfiction","Non-fiction","Autobiography"
                                                        ,"Biography","Memoir","Biography Memoir"])
    top_level_genres: list = field(default_factory=lambda: ['fiction', 'nonfiction', 'non-fiction'])